from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from leviathan_bt import sweep
from leviathan_bt.config import BacktestConfig, StrategyParams, SymbolSpec

# warmup = max(ema_trend*3, 1*2, 1+2): 3 with ema_trend=1, 9 with ema_trend=3
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
_CRASH_BAR = (100.0, 100.5, 95.0, 96.0)


def _frame(bars: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(bars), freq="h")
    return pd.DataFrame(bars, columns=["open", "high", "low", "close"], index=index)


def _signals(df: pd.DataFrame, entry_times: set[pd.Timestamp]) -> pd.DataFrame:
    # entry at bar i reads the signal at i-1, so flag the bar before each wanted entry
    next_bar_times = df.index + pd.Timedelta(hours=1)
    long_signal = np.array([time in entry_times for time in next_bar_times], dtype=bool)
    return pd.DataFrame(
        {
            "long_signal": long_signal,
            "short_signal": np.zeros(len(df), dtype=bool),
            "atr": np.full(len(df), 1.0),
            "swing_sl_long": np.full(len(df), np.nan),
            "swing_sl_short": np.full(len(df), np.nan),
        },
        index=df.index,
    )


def _signals_only_for_slow_trend(entry_times: set[pd.Timestamp]):
    def build(df: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
        wanted = entry_times if params.ema_trend == 3 else set()
        return _signals(df, wanted)

    return build


def _record_run_full(monkeypatch: pytest.MonkeyPatch) -> list[tuple[pd.Timestamp | None, list]]:
    calls: list[tuple[pd.Timestamp | None, list]] = []
    original = sweep.run_full

    def recording(df, params, symbol, config, window_start=None):
        result = original(df, params, symbol, config, window_start)
        calls.append((window_start, result[1]))
        return result

    monkeypatch.setattr(sweep, "run_full", recording)
    return calls


def test_walk_forward_warms_up_for_the_slowest_grid_combination(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _frame([_FLAT_BAR] * 40)
    is_bars, oos_bars = 10, 10
    first_is_start = 9
    is_start = df.index[first_is_start]
    oos_start = df.index[first_is_start + is_bars]
    monkeypatch.setattr(sweep, "build_signals", _signals_only_for_slow_trend({is_start, oos_start}))
    calls = _record_run_full(monkeypatch)

    result = sweep.walk_forward(
        df, _PARAMS, {"ema_trend": [1, 3]}, _SYMBOL, _CONFIG,
        is_bars=is_bars, oos_bars=oos_bars, step_bars=100, min_trades=1,
    )

    assert [step["is_start"] for step in result["steps"]] == [is_start]
    assert result["steps"][0]["params"] == {"ema_trend": 3}
    assert result["steps"][0]["oos_trades"] == 1
    oos_trades = [trades for window_start, trades in calls if window_start == oos_start]
    assert oos_trades[-1][0].entry_time == oos_start


def test_run_full_drawdown_ignores_losses_before_the_window(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _frame([_FLAT_BAR] * 5 + [_CRASH_BAR] + [_FLAT_BAR] * 10)
    monkeypatch.setattr(sweep, "build_signals", lambda frame, params: _signals(frame, {frame.index[4]}))

    whole, whole_trades, _ = sweep.run_full(df, _PARAMS, _SYMBOL, _CONFIG)
    windowed, windowed_trades, _ = sweep.run_full(df, _PARAMS, _SYMBOL, _CONFIG, window_start=df.index[8])

    assert len(whole_trades) == 1
    assert whole["max_drawdown"] > 0.0
    assert windowed_trades == []
    assert windowed["max_drawdown"] == 0.0
    assert windowed["max_drawdown_pct"] == 0.0
