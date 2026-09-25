from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

import pytest

pytest.importorskip("mcp")

DEMO = 0
REAL = 2
BID = 1.1000
ASK = 1.1002
SYMBOL_FILLING_FOK = 1
SYMBOL_FILLING_IOC = 2


class FakeMT5(SimpleNamespace):
    def __init__(self, trade_mode: int = DEMO, tick: SimpleNamespace | None = None) -> None:
        super().__init__(
            TIMEFRAME_M1=1, TIMEFRAME_M5=5, TIMEFRAME_M15=15, TIMEFRAME_M30=30,
            TIMEFRAME_H1=16385, TIMEFRAME_H4=16388, TIMEFRAME_D1=16408, TIMEFRAME_W1=32769,
            ACCOUNT_TRADE_MODE_DEMO=DEMO, ACCOUNT_TRADE_MODE_REAL=REAL,
            TRADE_ACTION_DEAL=1, ORDER_TYPE_BUY=0, ORDER_TYPE_SELL=1, ORDER_TIME_GTC=0,
            ORDER_FILLING_FOK=0, ORDER_FILLING_IOC=1, ORDER_FILLING_RETURN=2,
            TRADE_RETCODE_DONE=10009, POSITION_TYPE_BUY=0, POSITION_TYPE_SELL=1,
            DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1,
        )
        self.account = SimpleNamespace(login=123456, trade_mode=trade_mode)
        self.tick = tick if tick is not None else SimpleNamespace(bid=BID, ask=ASK, time=0)
        self.tick_available = True
        self.filling_mode = SYMBOL_FILLING_FOK
        self.symbol_available = True
        self.sent: list[dict] = []
        self.rates_requests: list[tuple] = []
        self.positions: tuple = ()

    def initialize(self) -> bool:
        return True

    def last_error(self) -> tuple:
        return (1, "fake")

    def account_info(self) -> SimpleNamespace:
        return self.account

    def symbol_select(self, symbol: str, enable: bool) -> bool:
        return True

    def symbol_info_tick(self, symbol: str) -> SimpleNamespace | None:
        return self.tick if self.tick_available else None

    def symbol_info(self, symbol: str) -> SimpleNamespace | None:
        if not self.symbol_available:
            return None
        return SimpleNamespace(filling_mode=self.filling_mode, point=0.00001)

    def positions_get(self, **kwargs) -> tuple:
        return self.positions

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start: int, count: int) -> list:
        self.rates_requests.append((symbol, timeframe, start, count))
        return []

    def order_send(self, request: dict) -> SimpleNamespace:
        self.sent.append(request)
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=1, price=request["price"], comment="done")


@pytest.fixture
def fake_mt5(monkeypatch: pytest.MonkeyPatch) -> FakeMT5:
    for name in ("LEVIATHAN_ALLOW_TRADING", "LEVIATHAN_ALLOW_REAL", "LEVIATHAN_MAX_LOTS"):
        monkeypatch.delenv(name, raising=False)
    fake = FakeMT5()
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    return fake


@pytest.fixture
def bridge(fake_mt5: FakeMT5, monkeypatch: pytest.MonkeyPatch):
    module = importlib.import_module("leviathan_bt.mt5_mcp")
    monkeypatch.setattr(module, "mt5", fake_mt5)
    return module


@pytest.fixture
def trading_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEVIATHAN_ALLOW_TRADING", "1")


def _long(bridge, lots: float = 0.10, sl: float = 1.0950, tp: float = 1.1100) -> str:
    return bridge.mt5_place_order("EURUSD", "long", lots, sl, tp)


def test_place_order_refused_without_allow_trading(bridge, fake_mt5):
    with pytest.raises(PermissionError):
        _long(bridge)
    assert fake_mt5.sent == []


def test_place_order_refuses_real_account_without_allow_real(bridge, fake_mt5, trading_on):
    fake_mt5.account.trade_mode = REAL
    with pytest.raises(PermissionError, match="NOT a demo"):
        _long(bridge)
    assert fake_mt5.sent == []


def test_place_order_on_demo_with_flag_sends_exactly_one_order(bridge, fake_mt5, trading_on):
    _long(bridge, lots=0.10, sl=1.0950, tp=1.1100)
    assert len(fake_mt5.sent) == 1
    request = fake_mt5.sent[0]
    assert request["volume"] == 0.10
    assert request["price"] == ASK
    assert (request["sl"], request["tp"]) == (1.0950, 1.1100)


def test_short_on_demo_with_valid_stops_is_sent_at_bid(bridge, fake_mt5, trading_on):
    bridge.mt5_place_order("EURUSD", "short", 0.10, sl=1.1050, tp=1.0900)
    assert fake_mt5.sent[0]["price"] == BID


@pytest.mark.parametrize("lots", [0.0, -0.10, float("nan")])
def test_place_order_rejects_non_positive_lots(bridge, fake_mt5, trading_on, lots):
    with pytest.raises(ValueError, match="lots"):
        _long(bridge, lots=lots)
    assert fake_mt5.sent == []


def test_place_order_rejects_lots_above_default_cap(bridge, fake_mt5, trading_on):
    with pytest.raises(ValueError, match="LEVIATHAN_MAX_LOTS"):
        _long(bridge, lots=bridge.DEFAULT_MAX_LOTS + 0.01)
    assert fake_mt5.sent == []


def test_place_order_rejects_lots_above_env_cap(bridge, fake_mt5, trading_on, monkeypatch):
    monkeypatch.setenv("LEVIATHAN_MAX_LOTS", "0.05")
    with pytest.raises(ValueError, match="LEVIATHAN_MAX_LOTS"):
        _long(bridge, lots=0.10)
    assert fake_mt5.sent == []


def test_env_cap_can_raise_the_limit(bridge, fake_mt5, trading_on, monkeypatch):
    monkeypatch.setenv("LEVIATHAN_MAX_LOTS", "5")
    _long(bridge, lots=2.0)
    assert fake_mt5.sent[0]["volume"] == 2.0


@pytest.mark.parametrize("raw", ["abc", "0", "-1", "nan"])
def test_invalid_env_cap_is_rejected(bridge, fake_mt5, trading_on, monkeypatch, raw):
    monkeypatch.setenv("LEVIATHAN_MAX_LOTS", raw)
    with pytest.raises(ValueError, match="LEVIATHAN_MAX_LOTS"):
        _long(bridge)
    assert fake_mt5.sent == []


@pytest.mark.parametrize(
    ("direction", "sl", "tp"),
    [
        ("long", 1.1010, 1.1100),
        ("long", 1.0950, 1.0990),
        ("short", 1.0990, 1.0900),
        ("short", 1.1050, 1.1010),
    ],
    ids=["long-sl-above", "long-tp-below", "short-sl-below", "short-tp-above"],
)
def test_place_order_rejects_stops_on_wrong_side(bridge, fake_mt5, trading_on, direction, sl, tp):
    with pytest.raises(ValueError, match="sl"):
        bridge.mt5_place_order("EURUSD", direction, 0.10, sl, tp)
    assert fake_mt5.sent == []


def test_place_order_without_tick_raises_runtime_error(bridge, fake_mt5, trading_on):
    fake_mt5.tick_available = False
    with pytest.raises(RuntimeError, match="no tick"):
        _long(bridge)
    assert fake_mt5.sent == []


def test_close_position_refused_without_allow_trading(bridge, fake_mt5):
    with pytest.raises(PermissionError):
        bridge.mt5_close_position(42)
    assert fake_mt5.sent == []


def test_close_position_without_tick_raises_runtime_error(bridge, fake_mt5, trading_on):
    fake_mt5.positions = (SimpleNamespace(symbol="EURUSD", type=fake_mt5.POSITION_TYPE_BUY, volume=0.10),)
    fake_mt5.tick_available = False
    with pytest.raises(RuntimeError, match="no tick"):
        bridge.mt5_close_position(42)
    assert fake_mt5.sent == []


@pytest.mark.parametrize("count", [0, -5])
def test_recent_bars_rejects_non_positive_count(bridge, fake_mt5, count):
    with pytest.raises(ValueError, match="count"):
        bridge.mt5_recent_bars("EURUSD", "H1", count)
    assert fake_mt5.rates_requests == []


def test_recent_bars_caps_count_at_1000(bridge, fake_mt5):
    bridge.mt5_recent_bars("EURUSD", "H1", 5000)
    assert fake_mt5.rates_requests[0][3] == 1000


def _open_long_position(fake: FakeMT5) -> None:
    fake.positions = (SimpleNamespace(symbol="EURUSD", type=fake.POSITION_TYPE_BUY, volume=0.10),)


FILLING_CASES = [
    (SYMBOL_FILLING_FOK, "ORDER_FILLING_FOK"),
    (SYMBOL_FILLING_IOC, "ORDER_FILLING_IOC"),
    (SYMBOL_FILLING_FOK | SYMBOL_FILLING_IOC, "ORDER_FILLING_FOK"),
    (0, "ORDER_FILLING_RETURN"),
]
FILLING_IDS = ["fok-only", "ioc-only", "fok-and-ioc-prefers-fok", "neither-uses-return"]


@pytest.mark.parametrize(("symbol_filling", "expected"), FILLING_CASES, ids=FILLING_IDS)
def test_place_order_uses_filling_mode_allowed_by_symbol(bridge, fake_mt5, trading_on, symbol_filling, expected):
    fake_mt5.filling_mode = symbol_filling
    _long(bridge)
    assert fake_mt5.sent[0]["type_filling"] == getattr(fake_mt5, expected)


@pytest.mark.parametrize(("symbol_filling", "expected"), FILLING_CASES, ids=FILLING_IDS)
def test_close_position_uses_filling_mode_allowed_by_symbol(bridge, fake_mt5, trading_on, symbol_filling, expected):
    _open_long_position(fake_mt5)
    fake_mt5.filling_mode = symbol_filling
    bridge.mt5_close_position(42)
    assert fake_mt5.sent[0]["type_filling"] == getattr(fake_mt5, expected)


def test_place_order_without_symbol_info_raises_runtime_error(bridge, fake_mt5, trading_on):
    fake_mt5.symbol_available = False
    with pytest.raises(RuntimeError, match="no symbol info"):
        _long(bridge)
    assert fake_mt5.sent == []


def test_close_position_without_symbol_info_raises_runtime_error(bridge, fake_mt5, trading_on):
    _open_long_position(fake_mt5)
    fake_mt5.symbol_available = False
    with pytest.raises(RuntimeError, match="no symbol info"):
        bridge.mt5_close_position(42)
    assert fake_mt5.sent == []
