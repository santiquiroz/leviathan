from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from leviathan_bt import sweep
from leviathan_bt.config import BacktestConfig, StrategyParams, SymbolSpec, load_toml
from leviathan_bt.data import load_csv
from leviathan_bt.strategy import warmup_bars

_PYTHON_DIR = Path(__file__).resolve().parents[1]
_SAMPLE = _PYTHON_DIR.parent / "data" / "sample" / "EURUSD_H1.csv"
_EXAMPLE_CONFIG = _PYTHON_DIR / "examples" / "config.example.toml"
_SAMPLE_GRID = {"atr_multiplier": [1.0, 2.0], "risk_reward": [1.5, 2.0]}

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


@pytest.fixture(scope="module")
def sample() -> tuple[pd.DataFrame, StrategyParams, SymbolSpec, BacktestConfig]:
    return (load_csv(_SAMPLE), *load_toml(_EXAMPLE_CONFIG))


def test_grid_search_serial_ranks_every_combination_by_profit_factor(sample) -> None:
    df, params, symbol, config = sample

    rows = sweep.grid_search(df, params, _SAMPLE_GRID, symbol, config, n_jobs=1, min_trades=1)

    assert sorted((row["params"]["atr_multiplier"], row["params"]["risk_reward"]) for row in rows) == [
        (1.0, 1.5), (1.0, 2.0), (2.0, 1.5), (2.0, 2.0)
    ]
    factors = [row["profit_factor"] for row in rows]
    assert factors == sorted(factors, reverse=True)


def test_grid_search_rows_match_a_single_run_with_the_same_overrides(sample) -> None:
    df, params, symbol, config = sample

    rows = sweep.grid_search(df, params, _SAMPLE_GRID, symbol, config, n_jobs=1, min_trades=1)

    for row in rows:
        expected = sweep.run(df, replace(params, **row["params"]), symbol, config)
        assert {key: value for key, value in row.items() if key != "params"} == expected


def test_grid_search_drops_combinations_below_min_trades(sample) -> None:
    df, params, symbol, config = sample
    all_rows = sweep.grid_search(df, params, _SAMPLE_GRID, symbol, config, n_jobs=1, min_trades=1)
    threshold = sorted(row["trades"] for row in all_rows)[1]

    kept = sweep.grid_search(df, params, _SAMPLE_GRID, symbol, config, n_jobs=1, min_trades=threshold)

    assert len(kept) == sum(1 for row in all_rows if row["trades"] >= threshold)
    assert all(row["trades"] >= threshold for row in kept)


def test_walk_forward_on_sample_data_steps_through_rolling_windows(sample) -> None:
    df, params, symbol, config = sample
    is_bars, oos_bars, step_bars = 1500, 500, 500
    grid = {"risk_reward": [1.5, 2.0]}
    starts = range(warmup_bars(params), len(df) - is_bars - oos_bars + 1, step_bars)

    result = sweep.walk_forward(
        df, params, grid, symbol, config, is_bars=is_bars, oos_bars=oos_bars, step_bars=step_bars, min_trades=1
    )

    steps = result["steps"]
    assert [step["is_start"] for step in steps] == [df.index[start] for start in starts]
    assert [step["oos_start"] for step in steps] == [df.index[start + is_bars] for start in starts]
    assert all(step["params"]["risk_reward"] in grid["risk_reward"] for step in steps)
    is_mean = sum(step["is_expectancy_r"] for step in steps) / len(steps)
    oos_mean = sum(step["oos_expectancy_r"] for step in steps) / len(steps)
    assert result["is_expectancy_r"] == pytest.approx(is_mean)
    assert result["oos_expectancy_r"] == pytest.approx(oos_mean)
    assert result["wf_efficiency"] == pytest.approx(oos_mean / is_mean)


def test_walk_forward_skips_windows_without_enough_in_sample_trades(sample) -> None:
    df, params, symbol, config = sample

    result = sweep.walk_forward(
        df, params, {"risk_reward": [2.0]}, symbol, config,
        is_bars=1500, oos_bars=500, step_bars=500, min_trades=10_000,
    )

    assert result == {"steps": [], "is_expectancy_r": 0.0, "oos_expectancy_r": 0.0, "wf_efficiency": 0.0}


def test_walk_forward_rejects_non_positive_step(sample) -> None:
    df, params, symbol, config = sample
    with pytest.raises(ValueError, match="step_bars"):
        sweep.walk_forward(df, params, {"risk_reward": [2.0]}, symbol, config, 1500, 500, 0)
