from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from . import data as data_module
from .config import BacktestConfig, StrategyParams, SymbolSpec, load_toml
from .sweep import grid_search as run_grid_search
from .sweep import run_full, walk_forward as run_walk_forward

try:
    from mcp.server import MCPServer
    from mcp.types import ToolAnnotations
except ImportError as exc:  # pragma: no cover
    raise RuntimeError('MCP support requires: pip install "leviathan-bt[mcp]"') from exc

mcp = MCPServer("leviathan_mcp")

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STRATEGY_SPEC = _REPO_ROOT / "docs" / "STRATEGY.md"

_STRATEGY_FIELDS = {f.name for f in dataclasses.fields(StrategyParams)}
_SYMBOL_FIELDS = {f.name for f in dataclasses.fields(SymbolSpec)}
_BACKTEST_FIELDS = {f.name for f in dataclasses.fields(BacktestConfig)}


def _load_setup(config_path: str | None, overrides: dict[str, Any] | None):
    if config_path:
        params, symbol, config = load_toml(config_path)
    else:
        params, symbol, config = StrategyParams(), SymbolSpec(), BacktestConfig()
    for key, value in (overrides or {}).items():
        if key in _STRATEGY_FIELDS:
            params = dataclasses.replace(params, **{key: value})
        elif key in _SYMBOL_FIELDS:
            symbol = dataclasses.replace(symbol, **{key: value})
        elif key in _BACKTEST_FIELDS:
            config = dataclasses.replace(config, **{key: value})
        else:
            raise ValueError(
                f"unknown override '{key}'. Valid keys: strategy {sorted(_STRATEGY_FIELDS)}, "
                f"symbol {sorted(_SYMBOL_FIELDS)}, backtest {sorted(_BACKTEST_FIELDS)}"
            )
    return params, symbol, config


def _trade_row(trade: Any) -> dict[str, Any]:
    return {
        "entry_time": str(trade.entry_time),
        "exit_time": str(trade.exit_time),
        "direction": "long" if trade.direction == 1 else "short",
        "entry": trade.entry_price,
        "exit": trade.exit_price,
        "sl": trade.sl,
        "tp": trade.tp,
        "lots": trade.lots,
        "pnl": round(trade.pnl, 2),
        "r_multiple": round(trade.r_multiple, 3),
        "exit_reason": trade.exit_reason,
        "ambiguous": bool(trade.ambiguous),
    }


@mcp.tool(
    name="leviathan_run_backtest",
    title="Run a Leviathan backtest",
    annotations=READ_ONLY,
)
def leviathan_run_backtest(
    data_path: str,
    config_path: str | None = None,
    overrides: dict[str, Any] | None = None,
    last_trades: int = 10,
) -> str:
    """Run one backtest of the Leviathan strategy on an OHLCV CSV (MT5 export or Binance kline format).

    Without config_path the spec defaults are used (EURUSD 5-digit symbol spec). overrides is a flat
    dict of any StrategyParams / SymbolSpec / BacktestConfig field, e.g. {"atr_multiplier": 2.0,
    "risk_reward": 3.0, "spread_points": 15}. Returns JSON: summary metrics + the last N trades.
    """
    df = data_module.load_csv(data_path)
    params, symbol, config = _load_setup(config_path, overrides)
    summary, trades, _ = run_full(df, params, symbol, config)
    return json.dumps(
        {
            "data": {"path": data_path, "bars": len(df), "start": str(df.index[0]), "end": str(df.index[-1])},
            "summary": summary,
            "last_trades": [_trade_row(t) for t in trades[-max(0, last_trades):]],
        },
        indent=2,
    )


@mcp.tool(
    name="leviathan_grid_search",
    title="Grid-search strategy parameters",
    annotations=READ_ONLY,
)
def leviathan_grid_search(
    data_path: str,
    grid: dict[str, list[Any]],
    config_path: str | None = None,
    min_trades: int = 30,
    max_results: int = 10,
) -> str:
    """Test every combination of the given parameter grid and rank results by profit factor.

    grid maps StrategyParams fields to candidate values, e.g. {"atr_multiplier": [1.0, 1.5, 2.0],
    "risk_reward": [1.5, 2.0, 3.0]}. Combinations with fewer than min_trades trades are dropped
    (too little evidence). Returns JSON rows: parameter overrides + summary metrics each.
    WARNING for interpretation: in-sample winners are usually overfit - verify with
    leviathan_walk_forward before trusting any ranking.
    """
    df = data_module.load_csv(data_path)
    params, symbol, config = _load_setup(config_path, None)
    rows = run_grid_search(df, params, grid, symbol, config, n_jobs=1, min_trades=min_trades)
    return json.dumps({"tested": len(rows), "top": rows[:max_results]}, indent=2, default=str)


@mcp.tool(
    name="leviathan_walk_forward",
    title="Walk-forward validation",
    annotations=READ_ONLY,
)
def leviathan_walk_forward(
    data_path: str,
    grid: dict[str, list[Any]],
    is_bars: int = 4000,
    oos_bars: int = 1000,
    step_bars: int = 1000,
    config_path: str | None = None,
) -> str:
    """Rolling walk-forward: optimize the grid in-sample, test the winner out-of-sample, step forward.

    The honest way to evaluate a parameter sweep. Returns JSON with per-step results and
    wf_efficiency (out-of-sample R / in-sample R) - values below ~0.5 suggest overfitting.
    """
    df = data_module.load_csv(data_path)
    params, symbol, config = _load_setup(config_path, None)
    result = run_walk_forward(df, params, grid, symbol, config, is_bars, oos_bars, step_bars)
    return json.dumps(result, indent=2, default=str)


@mcp.tool(
    name="leviathan_describe_data",
    title="Describe an OHLCV data file",
    annotations=READ_ONLY,
)
def leviathan_describe_data(data_path: str) -> str:
    """Inspect an OHLCV CSV before backtesting: bar count, date range, inferred timeframe, gaps, price stats."""
    df = data_module.load_csv(data_path)
    deltas = df.index.to_series().diff().dropna()
    typical = deltas.mode().iloc[0] if len(deltas) else None
    gaps = int((deltas > typical * 1.5).sum()) if typical is not None else 0
    return json.dumps(
        {
            "path": data_path,
            "bars": len(df),
            "start": str(df.index[0]),
            "end": str(df.index[-1]),
            "inferred_timeframe": str(typical),
            "gaps_over_1p5x_timeframe": gaps,
            "close_min": float(df["close"].min()),
            "close_max": float(df["close"].max()),
            "columns": list(df.columns),
        },
        indent=2,
    )


@mcp.tool(
    name="leviathan_get_strategy_spec",
    title="Get the Leviathan strategy specification",
    annotations=READ_ONLY,
)
def leviathan_get_strategy_spec() -> str:
    """Return docs/STRATEGY.md - the exact trading rules both the EA and this backtester implement."""
    if not _STRATEGY_SPEC.exists():
        raise FileNotFoundError(f"strategy spec not found at {_STRATEGY_SPEC} (running outside the repo?)")
    return _STRATEGY_SPEC.read_text(encoding="utf-8")


@mcp.tool(
    name="leviathan_read_ea_signals",
    title="Read the MT5 EA signal log",
    annotations=READ_ONLY,
)
def leviathan_read_ea_signals(csv_path: str, last: int = 20) -> str:
    """Read the signal log the Leviathan EA writes when 'Log signals to file' is enabled.

    The file lives in the MT5 data folder under MQL5/Files/Leviathan_signals.csv. Columns:
    time, symbol, timeframe, direction, pattern, entry, sl, tp, lots. Returns the last N signals
    as JSON so they can be analyzed against backtest expectations.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found. In MT5: enable 'Log signals to file' in the EA inputs, then "
            "locate the file via File -> Open Data Folder -> MQL5/Files/Leviathan_signals.csv"
        )
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    header = ["time", "symbol", "timeframe", "direction", "pattern", "entry", "sl", "tp", "lots"]
    rows = [dict(zip(header, line.split(";"))) for line in lines[-max(0, last):]]
    return json.dumps({"total_signals": len(lines), "last": rows}, indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
