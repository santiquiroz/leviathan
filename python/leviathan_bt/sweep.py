from __future__ import annotations

import itertools
import math
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from functools import partial
from typing import Any

import pandas as pd

from .config import BacktestConfig, StrategyParams, SymbolSpec
from .engine import run_backtest
from .metrics import summarize
from .strategy import build_signals, warmup_bars

RunResult = tuple[dict[str, Any], list[Any], pd.Series]


def run(
    df: pd.DataFrame,
    params: StrategyParams,
    symbol: SymbolSpec,
    config: BacktestConfig,
) -> dict[str, Any]:
    summary, _, _ = run_full(df, params, symbol, config)
    return summary


def run_full(
    df: pd.DataFrame,
    params: StrategyParams,
    symbol: SymbolSpec,
    config: BacktestConfig,
    window_start: pd.Timestamp | None = None,
) -> RunResult:
    signals = build_signals(df, params)
    raw_trades, equity_curve = run_backtest(df, signals, params, symbol, config)
    trades = _counted_trades(raw_trades, window_start)
    summary = summarize(trades, equity_curve, config.initial_equity)
    return summary, trades, equity_curve


def grid_search(
    df: pd.DataFrame,
    base_params: StrategyParams,
    grid: dict[str, list[Any]],
    symbol: SymbolSpec,
    config: BacktestConfig,
    n_jobs: int | None = None,
    min_trades: int = 30,
    window_start: pd.Timestamp | None = None,
) -> list[dict[str, Any]]:
    combos = _grid_combinations(grid)
    worker = partial(_evaluate_overrides, df, base_params, symbol, config, window_start)
    rows = _map_combinations(worker, combos, n_jobs)
    kept = [row for row in rows if int(row["trades"]) >= min_trades]
    return sorted(kept, key=_profit_factor_key, reverse=True)


def walk_forward(
    df: pd.DataFrame,
    base_params: StrategyParams,
    grid: dict[str, list[Any]],
    symbol: SymbolSpec,
    config: BacktestConfig,
    is_bars: int,
    oos_bars: int,
    step_bars: int,
    min_trades: int = 10,
) -> dict[str, Any]:
    if step_bars <= 0:
        raise ValueError("step_bars must be positive")
    warmup = warmup_bars(base_params)
    steps: list[dict[str, Any]] = []
    for start in range(warmup, len(df) - is_bars - oos_bars + 1, step_bars):
        step = _walk_forward_step(
            df, base_params, grid, symbol, config, start, is_bars, oos_bars, warmup, min_trades
        )
        if step is not None:
            steps.append(step)
    return _walk_forward_totals(steps)


def _walk_forward_step(
    df: pd.DataFrame,
    base_params: StrategyParams,
    grid: dict[str, list[Any]],
    symbol: SymbolSpec,
    config: BacktestConfig,
    start: int,
    is_bars: int,
    oos_bars: int,
    warmup: int,
    min_trades: int,
) -> dict[str, Any] | None:
    is_slice = df.iloc[start - warmup : start + is_bars]
    oos_pos = start + is_bars
    oos_slice = df.iloc[oos_pos - warmup : oos_pos + oos_bars]
    # n_jobs=1 keeps the inner grid serial so pools never nest
    ranked = grid_search(
        is_slice, base_params, grid, symbol, config,
        n_jobs=1, min_trades=min_trades, window_start=df.index[start],
    )
    if not ranked:
        return None
    best = ranked[0]
    best_params = replace(base_params, **best["params"])
    oos_summary, _, _ = run_full(oos_slice, best_params, symbol, config, window_start=df.index[oos_pos])
    return _step_row(df.index[start], df.index[oos_pos], best, oos_summary)


def _step_row(
    is_start: pd.Timestamp,
    oos_start: pd.Timestamp,
    best: dict[str, Any],
    oos_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "is_start": is_start,
        "oos_start": oos_start,
        "params": best["params"],
        "is_trades": int(best["trades"]),
        "is_profit_factor": float(best["profit_factor"]),
        "is_expectancy_r": float(best["expectancy_r"]),
        "oos_trades": int(oos_summary["trades"]),
        "oos_profit_factor": float(oos_summary["profit_factor"]),
        "oos_expectancy_r": float(oos_summary["expectancy_r"]),
    }


def _walk_forward_totals(steps: list[dict[str, Any]]) -> dict[str, Any]:
    is_mean = _mean([step["is_expectancy_r"] for step in steps])
    oos_mean = _mean([step["oos_expectancy_r"] for step in steps])
    efficiency = oos_mean / is_mean if is_mean != 0.0 else 0.0
    return {
        "steps": steps,
        "is_expectancy_r": is_mean,
        "oos_expectancy_r": oos_mean,
        "wf_efficiency": efficiency,
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _evaluate_overrides(
    df: pd.DataFrame,
    base_params: StrategyParams,
    symbol: SymbolSpec,
    config: BacktestConfig,
    window_start: pd.Timestamp | None,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    params = replace(base_params, **overrides)
    summary, _, _ = run_full(df, params, symbol, config, window_start)
    return {"params": overrides, **summary}


def _grid_combinations(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    names = sorted(grid)
    products = itertools.product(*(grid[name] for name in names))
    return [dict(zip(names, values)) for values in products]


def _map_combinations(
    worker: Callable[[dict[str, Any]], dict[str, Any]],
    combos: list[dict[str, Any]],
    n_jobs: int | None,
) -> list[dict[str, Any]]:
    if n_jobs == 1:
        return [worker(overrides) for overrides in combos]
    with ProcessPoolExecutor(max_workers=n_jobs) as pool:
        return list(pool.map(worker, combos))


def _profit_factor_key(row: dict[str, Any]) -> float:
    value = float(row["profit_factor"])
    return float("-inf") if math.isnan(value) else value


def _counted_trades(trades: Any, window_start: pd.Timestamp | None) -> list[Any]:
    if window_start is None:
        return list(trades)
    return [trade for trade in trades if _entry_time(trade) >= window_start]


def _entry_time(trade: Any) -> pd.Timestamp:
    value = trade["entry_time"] if isinstance(trade, dict) else trade.entry_time
    return pd.Timestamp(value)
