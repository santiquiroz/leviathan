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


def _frame(bars: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(bars), freq="h")
    return pd.DataFrame(bars, columns=["open", "high", "low", "close"], index=index)


def _signals(df: pd.DataFrame, long_rows: tuple[int, ...], atr_value: float = 1.0) -> pd.DataFrame:
    long_signal = np.zeros(len(df), dtype=bool)
    long_signal[list(long_rows)] = True
    return pd.DataFrame(
        {
            "long_signal": long_signal,
            "short_signal": np.zeros(len(df), dtype=bool),
            "atr": np.full(len(df), atr_value),
            "swing_sl_long": np.full(len(df), np.nan),
            "swing_sl_short": np.full(len(df), np.nan),
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
    # entry 100.03, SL 98.53, TP 103.03 all inside the 98..104 bar
    assert trade.exit_reason == "sl"
    assert trade.ambiguous is True
    assert trade.exit_price == pytest.approx(98.53 - 0.01)
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
