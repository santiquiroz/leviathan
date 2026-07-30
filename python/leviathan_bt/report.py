from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import pandas as pd

_TRADES_TAIL = 10


def text_report(summary: dict[str, Any], trades: Sequence[Any]) -> str:
    return f"{_summary_block(summary)}\n\n{_trades_block(trades)}"


def save_equity_png(equity_curve: Any, path: str | Path) -> None:
    try:
        import matplotlib
    except ImportError as error:
        raise RuntimeError('pip install "leviathan-bt[plot]"') from error
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    curve = pd.Series(equity_curve, dtype=float)
    peak = curve.cummax()
    figure, axis = plt.subplots(figsize=(10, 5))
    axis.plot(curve.index, curve.to_numpy(), color="#1f6f8b", linewidth=1.2, label="equity")
    axis.fill_between(curve.index, curve.to_numpy(), peak.to_numpy(), color="#c0392b", alpha=0.25, label="drawdown")
    axis.set_title("Leviathan equity curve")
    axis.set_ylabel("equity")
    axis.legend(loc="best")
    figure.tight_layout()
    figure.savefig(Path(path), dpi=120)
    plt.close(figure)


def _summary_block(summary: dict[str, Any]) -> str:
    if not summary:
        return "no summary"
    width = max(len(str(key)) for key in summary)
    lines = [f"{str(key).ljust(width)} : {_format_value(value)}" for key, value in summary.items()]
    return "\n".join(lines)


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _trades_block(trades: Sequence[Any]) -> str:
    frame = _recent_trades_frame(trades)
    if frame.empty:
        return "no trades"
    return f"last {len(frame)} trades\n{frame.to_string(index=False)}"


def _recent_trades_frame(trades: Any) -> pd.DataFrame:
    if isinstance(trades, pd.DataFrame):
        return trades.tail(_TRADES_TAIL)
    rows = [_trade_mapping(trade) for trade in list(trades)[-_TRADES_TAIL:]]
    return pd.DataFrame(rows)


def _trade_mapping(trade: Any) -> dict[str, Any]:
    if isinstance(trade, dict):
        return trade
    if is_dataclass(trade):
        return asdict(trade)
    if hasattr(trade, "_asdict"):
        return trade._asdict()
    return vars(trade)
