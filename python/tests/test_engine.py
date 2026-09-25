from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from leviathan_bt.config import BacktestConfig, StrategyParams, SymbolSpec
from leviathan_bt.engine import run_backtest

# warmup = max(1*3, 1*2, 1+2) = 3 -> first tradable bar is index 3, signal read at index 2
_PARAMS = StrategyParams(
    ema_fast=1,
    ema_slow=1,
    ema_trend=1,
    structure_lookback=1,
    atr_period=1,
    swing_lookback=1,
)
_SYMBOL = SymbolSpec(
    name="TEST",
    digits=2,
    point=0.01,
    pip_size=0.01,
    contract_size=1.0,
    spread_points=2.0,
    slippage_points=1.0,
    commission_per_lot=0.0,
    lot_step=0.01,
    lot_min=0.01,
    lot_max=100.0,
    tick_value=1.0,
    tick_size=0.01,
)
_CONFIG = BacktestConfig(initial_equity=10_000.0, lot_size=0.10)
_FLAT_BAR = (100.0, 100.5, 99.5, 100.0)


def _frame(bars: list[tuple[float, float, float, float]], start: str = "2024-01-01") -> pd.DataFrame:
    index = pd.date_range(start, periods=len(bars), freq="h")
    return pd.DataFrame(bars, columns=["open", "high", "low", "close"], index=index)


def _signals(
    df: pd.DataFrame,
    long_rows: tuple[int, ...],
    atr_value: float = 1.0,
    short_rows: tuple[int, ...] = (),
    swing_long: float = np.nan,
    swing_short: float = np.nan,
) -> pd.DataFrame:
    long_signal = np.zeros(len(df), dtype=bool)
    long_signal[list(long_rows)] = True
    short_signal = np.zeros(len(df), dtype=bool)
    short_signal[list(short_rows)] = True
    return pd.DataFrame(
        {
            "long_signal": long_signal,
            "short_signal": short_signal,
            "atr": np.full(len(df), atr_value),
            "swing_sl_long": np.full(len(df), swing_long),
            "swing_sl_short": np.full(len(df), swing_short),
        },
        index=df.index,
    )


def test_long_entry_fills_at_open_plus_spread_plus_slippage() -> None:
    df = _frame([_FLAT_BAR] * 5)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, _CONFIG)
    assert len(trades) == 1
    assert trades[0].direction == 1
    assert trades[0].entry_time == df.index[3]
    assert trades[0].entry_price == pytest.approx(100.0 + 0.02 + 0.01)


def test_bar_covering_sl_and_tp_exits_as_worst_case_sl() -> None:
    df = _frame([_FLAT_BAR, _FLAT_BAR, _FLAT_BAR, (100.0, 104.0, 98.0, 101.0), _FLAT_BAR])
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, _CONFIG)
    assert len(trades) == 1
    trade = trades[0]
    # SL 98.52 and TP 103.02 (anchored to the ask 100.02) both inside the 98..104 bar
    assert trade.exit_reason == "sl"
    assert trade.ambiguous is True
    assert trade.exit_price == pytest.approx(98.52 - 0.01)
    assert trade.exit_time == df.index[3]


def test_risk_percent_sizing_floors_to_lot_step() -> None:
    df = _frame([_FLAT_BAR] * 5)
    config = replace(_CONFIG, sizing_mode="risk_percent", risk_percent=1.0)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, config)
    # risk 100.0 over 150 points at 1.0/point -> 0.6667 raw, floored to 0.66
    assert trades[0].lots == pytest.approx(0.66)


def test_risk_percent_sizing_clamps_to_lot_min() -> None:
    df = _frame([_FLAT_BAR] * 5)
    config = replace(_CONFIG, sizing_mode="risk_percent", risk_percent=0.001)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, config)
    assert trades[0].lots == pytest.approx(_SYMBOL.lot_min)


def test_risk_percent_sizing_clamps_to_lot_max() -> None:
    df = _frame([_FLAT_BAR] * 5)
    symbol = replace(_SYMBOL, lot_max=0.5)
    config = replace(_CONFIG, sizing_mode="risk_percent", risk_percent=1.0)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, symbol, config)
    assert trades[0].lots == pytest.approx(0.5)


def test_one_position_only_ignores_second_signal_while_open() -> None:
    df = _frame([_FLAT_BAR] * 6)
    trades, _ = run_backtest(df, _signals(df, (2, 3)), _PARAMS, _SYMBOL, _CONFIG)
    assert len(trades) == 1
    assert trades[0].entry_time == df.index[3]


def test_end_of_data_force_closes_open_position() -> None:
    df = _frame([_FLAT_BAR] * 5)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, _CONFIG)
    trade = trades[0]
    assert trade.exit_reason == "end"
    assert trade.ambiguous is False
    assert trade.exit_time == df.index[4]
    # longs close on the bid, i.e. the raw chart close
    assert trade.exit_price == pytest.approx(100.0)


_BE_CONFIG = replace(_CONFIG, use_breakeven=True, breakeven_offset_points=5.0)


def test_long_sl_and_tp_anchor_to_ask_without_slippage() -> None:
    df = _frame([_FLAT_BAR] * 5)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, _CONFIG)
    trade = trades[0]
    ask = 100.0 + 0.02
    assert trade.entry_price == pytest.approx(ask + 0.01)
    assert trade.sl == pytest.approx(ask - 1.0 * _PARAMS.atr_multiplier)
    assert trade.tp == pytest.approx(ask + 1.0 * _PARAMS.atr_multiplier * _PARAMS.risk_reward)


def test_short_sl_and_tp_anchor_to_bid_without_slippage() -> None:
    df = _frame([_FLAT_BAR] * 5)
    trades, _ = run_backtest(df, _signals(df, (), short_rows=(2,)), _PARAMS, _SYMBOL, _CONFIG)
    trade = trades[0]
    bid = 100.0
    assert trade.direction == -1
    assert trade.entry_price == pytest.approx(bid - 0.01)
    assert trade.sl == pytest.approx(bid + 1.0 * _PARAMS.atr_multiplier)
    assert trade.tp == pytest.approx(bid - 1.0 * _PARAMS.atr_multiplier * _PARAMS.risk_reward)


def test_long_breakeven_ignores_previous_high_when_open_is_below_trigger() -> None:
    # fill 100.03, risk 1.5 -> +1R at bid 101.53; bar 3 high reaches it, bar 4 opens below it
    bars = [_FLAT_BAR] * 3 + [(100.0, 101.6, 99.5, 101.0), (101.0, 101.2, 100.0, 101.0), (101.0, 101.2, 100.5, 101.0)]
    df = _frame(bars)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, _BE_CONFIG)
    trade = trades[0]
    assert trade.exit_reason == "end"
    assert trade.sl == pytest.approx(98.52)


def test_long_breakeven_moves_sl_when_open_bid_reaches_trigger() -> None:
    bars = [_FLAT_BAR] * 3 + [(100.0, 101.0, 99.5, 101.0), (101.6, 101.8, 101.0, 101.6)]
    df = _frame(bars)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, _BE_CONFIG)
    trade = trades[0]
    assert trade.exit_reason == "end"
    assert trade.sl == pytest.approx(100.03 + 0.05)


def test_short_breakeven_ignores_previous_low_when_open_ask_is_above_trigger() -> None:
    # fill 99.99, risk 1.5 -> +1R at ask 98.49; bar 4 opens at bid 98.48, i.e. ask 98.50
    bars = [_FLAT_BAR] * 3 + [(100.0, 100.2, 98.0, 98.5), (98.48, 98.9, 98.3, 98.5), (98.5, 98.9, 98.3, 98.5)]
    df = _frame(bars)
    trades, _ = run_backtest(df, _signals(df, (), short_rows=(2,)), _PARAMS, _SYMBOL, _BE_CONFIG)
    trade = trades[0]
    assert trade.exit_reason == "end"
    assert trade.sl == pytest.approx(101.5)


def test_short_breakeven_moves_sl_when_open_ask_reaches_trigger() -> None:
    bars = [_FLAT_BAR] * 3 + [(100.0, 100.2, 99.0, 99.0), (98.46, 98.9, 98.3, 98.5)]
    df = _frame(bars)
    trades, _ = run_backtest(df, _signals(df, (), short_rows=(2,)), _PARAMS, _SYMBOL, _BE_CONFIG)
    trade = trades[0]
    assert trade.exit_reason == "end"
    assert trade.sl == pytest.approx(99.99 - 0.05)


def _short_trade(bars: list[tuple[float, float, float, float]], config: BacktestConfig = _CONFIG):
    df = _frame(bars)
    trades, _ = run_backtest(df, _signals(df, (), short_rows=(2,)), _PARAMS, _SYMBOL, config)
    assert len(trades) == 1
    return trades[0], df


def test_short_sl_triggers_on_ask_high_although_bid_high_stays_below_stop() -> None:
    # fill 99.99, SL 101.50: bid high 101.49 is an ask high of 101.51
    trade, df = _short_trade([_FLAT_BAR] * 3 + [(100.0, 101.49, 99.5, 100.0), _FLAT_BAR])
    assert trade.exit_reason == "sl"
    assert trade.exit_time == df.index[3]
    assert trade.exit_price == pytest.approx(101.5 + 0.01)
    assert trade.pnl < 0.0


def test_short_sl_ignored_while_ask_high_stays_below_stop() -> None:
    trade, _ = _short_trade([_FLAT_BAR] * 3 + [(100.0, 101.47, 99.5, 100.0), _FLAT_BAR])
    assert trade.exit_reason == "end"
    # shorts buy back at the ask
    assert trade.exit_price == pytest.approx(100.0 + 0.02)


def test_short_tp_needs_the_ask_low_to_reach_target() -> None:
    # TP 97.00: bid low 96.99 is an ask low of 97.01
    trade, _ = _short_trade([_FLAT_BAR] * 3 + [(100.0, 100.2, 96.99, 97.5), (97.5, 97.8, 97.2, 97.5)])
    assert trade.exit_reason == "end"


def test_short_tp_fills_at_target_when_ask_low_reaches_it() -> None:
    trade, df = _short_trade([_FLAT_BAR] * 3 + [(100.0, 100.2, 96.97, 97.5), _FLAT_BAR])
    assert trade.exit_reason == "tp"
    assert trade.exit_time == df.index[3]
    assert trade.exit_price == pytest.approx(97.0)
    assert trade.pnl > 0.0


_SWING_PARAMS = replace(_PARAMS, sl_mode="swing")


def test_swing_mode_long_uses_previous_swing_low_as_stop() -> None:
    df = _frame([_FLAT_BAR] * 5)
    signals = _signals(df, (2,), swing_long=99.0)
    trades, _ = run_backtest(df, signals, _SWING_PARAMS, _SYMBOL, _CONFIG)
    trade = trades[0]
    ask = 100.0 + 0.02
    assert trade.sl == pytest.approx(99.0)
    assert trade.tp == pytest.approx(ask + (ask - 99.0) * _PARAMS.risk_reward)


def test_swing_mode_short_uses_previous_swing_high_as_stop() -> None:
    df = _frame([_FLAT_BAR] * 5)
    signals = _signals(df, (), short_rows=(2,), swing_short=101.0)
    trades, _ = run_backtest(df, signals, _SWING_PARAMS, _SYMBOL, _CONFIG)
    trade = trades[0]
    assert trade.sl == pytest.approx(101.0)
    assert trade.tp == pytest.approx(100.0 - 1.0 * _PARAMS.risk_reward)


@pytest.mark.parametrize("swing_long", [np.nan, 100.02, 100.5])
def test_swing_mode_skips_long_when_swing_stop_is_missing_or_not_below_ask(swing_long: float) -> None:
    df = _frame([_FLAT_BAR] * 5)
    signals = _signals(df, (2,), swing_long=swing_long)
    trades, _ = run_backtest(df, signals, _SWING_PARAMS, _SYMBOL, _CONFIG)
    assert trades == []


@pytest.mark.parametrize("swing_short", [np.nan, 100.0, 99.5])
def test_swing_mode_skips_short_when_swing_stop_is_missing_or_not_above_bid(swing_short: float) -> None:
    df = _frame([_FLAT_BAR] * 5)
    signals = _signals(df, (), short_rows=(2,), swing_short=swing_short)
    trades, _ = run_backtest(df, signals, _SWING_PARAMS, _SYMBOL, _CONFIG)
    assert trades == []


_TRAIL_CONFIG = replace(_CONFIG, use_trailing=True, trailing_atr_mult=1.0)


def test_long_trailing_stop_follows_previous_close_minus_atr() -> None:
    # fill 100.03: bar 3 closes 101.5, so bar 4 trails the SL to 100.5
    bars = [_FLAT_BAR] * 3 + [(100.0, 101.6, 99.5, 101.5), (101.5, 101.8, 100.6, 101.6)]
    df = _frame(bars)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, _TRAIL_CONFIG)
    assert trades[0].exit_reason == "end"
    assert trades[0].sl == pytest.approx(100.5)


def test_long_trailing_stop_never_loosens() -> None:
    # bar 4 closes 101.2 (candidate 100.2 < SL 100.5); bar 5 low 100.4 hits only the kept 100.5
    bars = [_FLAT_BAR] * 3 + [
        (100.0, 101.6, 99.5, 101.5),
        (101.5, 101.8, 100.6, 101.2),
        (101.2, 101.4, 100.4, 101.0),
        _FLAT_BAR,
    ]
    df = _frame(bars)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, _TRAIL_CONFIG)
    trade = trades[0]
    assert trade.exit_reason == "sl"
    assert trade.exit_time == df.index[5]
    assert trade.exit_price == pytest.approx(100.5 - 0.01)


def test_long_trailing_stop_waits_until_candidate_reaches_entry() -> None:
    # bar 3 closes 100.9: candidate 99.9 is tighter than 98.52 but still below the 100.03 fill
    bars = [_FLAT_BAR] * 3 + [(100.0, 101.0, 99.5, 100.9), (100.9, 101.0, 100.5, 100.9)]
    df = _frame(bars)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, _TRAIL_CONFIG)
    assert trades[0].sl == pytest.approx(98.52)


def test_short_trailing_stop_never_loosens() -> None:
    # fill 99.99: bar 3 closes 98.0 (SL 99.0), bar 4 closes 98.6 (candidate 99.6 rejected),
    # bar 5 ask high 99.12 hits only the kept 99.0
    trade, df = _short_trade(
        [_FLAT_BAR] * 3
        + [(100.0, 100.2, 97.9, 98.0), (98.0, 98.9, 97.9, 98.6), (98.6, 99.1, 98.4, 98.9), _FLAT_BAR],
        _TRAIL_CONFIG,
    )
    assert trade.exit_reason == "sl"
    assert trade.exit_time == df.index[5]
    assert trade.exit_price == pytest.approx(99.0 + 0.01)


@pytest.mark.parametrize(
    ("start_hour", "end_hour", "expected_trades"),
    [
        (7, 20, 0),
        (3, 4, 1),
        (0, 3, 0),
        (22, 6, 1),
        (22, 3, 0),
        (5, 5, 1),
    ],
)
def test_session_filter_gates_entry_by_the_entry_bar_hour(
    start_hour: int, end_hour: int, expected_trades: int
) -> None:
    # the entry bar is 03:00
    df = _frame([_FLAT_BAR] * 5)
    config = replace(
        _CONFIG, use_session_filter=True, session_start_hour=start_hour, session_end_hour=end_hour
    )
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, config)
    assert len(trades) == expected_trades


@pytest.mark.parametrize(("start_hour", "end_hour", "expected_trades"), [(22, 6, 1), (0, 6, 0), (23, 22, 1)])
def test_session_window_crossing_midnight_allows_late_evening_entries(
    start_hour: int, end_hour: int, expected_trades: int
) -> None:
    # frame starts at 20:00, so the entry bar is 23:00
    df = _frame([_FLAT_BAR] * 5, start="2023-12-31 20:00")
    config = replace(
        _CONFIG, use_session_filter=True, session_start_hour=start_hour, session_end_hour=end_hour
    )
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, config)
    assert len(trades) == expected_trades


def test_session_filter_is_ignored_when_disabled() -> None:
    df = _frame([_FLAT_BAR] * 5)
    config = replace(_CONFIG, session_start_hour=7, session_end_hour=20)
    trades, _ = run_backtest(df, _signals(df, (2,)), _PARAMS, _SYMBOL, config)
    assert len(trades) == 1
