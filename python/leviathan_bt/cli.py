from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from . import data, sweep
from .config import load_toml
from .report import save_equity_png, text_report

_TOP_ROWS = 10


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "backtest":
        return _cmd_backtest(args)
    return _cmd_sweep(args)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="leviathan-bt", description="Leviathan price-action backtester")
    commands = parser.add_subparsers(dest="command", required=True)
    _add_backtest_parser(commands)
    _add_sweep_parser(commands)
    return parser.parse_args(argv)


def _add_backtest_parser(commands: Any) -> None:
    backtest = commands.add_parser("backtest", help="run a single backtest")
    backtest.add_argument("--data", required=True, help="OHLCV CSV (MT5 export)")
    backtest.add_argument("--config", required=True, help="TOML config file")
    backtest.add_argument("--out", help="write the text report to this file")
    backtest.add_argument("--plot", help="write an equity-curve PNG to this file")


def _add_sweep_parser(commands: Any) -> None:
    sweep_cmd = commands.add_parser("sweep", help="grid-search strategy parameters")
    sweep_cmd.add_argument("--data", required=True, help="OHLCV CSV (MT5 export)")
    sweep_cmd.add_argument("--config", required=True, help="TOML config file")
    sweep_cmd.add_argument("--grid", required=True, help="JSON file of {param: [values]}")
    sweep_cmd.add_argument("--jobs", type=int, default=None, help="worker processes")


def _cmd_backtest(args: argparse.Namespace) -> int:
    df = data.load_csv(args.data)
    params, symbol, config = load_toml(args.config)
    summary, trades, equity_curve = sweep.run_full(df, params, symbol, config)
    report = text_report(summary, trades)
    print(report)
    if args.out:
        Path(args.out).write_text(report + "\n", encoding="utf-8")
    if args.plot:
        save_equity_png(equity_curve, args.plot)
    return 0


def _cmd_sweep(args: argparse.Namespace) -> int:
    df = data.load_csv(args.data)
    params, symbol, config = load_toml(args.config)
    grid = _load_grid(args.grid)
    rows = sweep.grid_search(df, params, grid, symbol, config, n_jobs=args.jobs)
    print(_top_rows_table(rows))
    return 0


def _load_grid(path: str) -> dict[str, list[Any]]:
    grid = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(grid, dict) or not all(isinstance(values, list) for values in grid.values()):
        raise SystemExit("grid file must be a JSON object of {param: [values]}")
    return grid


def _top_rows_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "no parameter set produced enough trades"
    flattened = [_flatten_row(row) for row in rows[:_TOP_ROWS]]
    return pd.DataFrame(flattened).to_string(index=False)


def _flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    overrides = row.get("params", {})
    metrics = {key: value for key, value in row.items() if key != "params"}
    return {**overrides, **metrics}


if __name__ == "__main__":
    raise SystemExit(main())
