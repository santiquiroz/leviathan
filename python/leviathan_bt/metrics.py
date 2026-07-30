from __future__ import annotations

import math

import pandas as pd

from .engine import Trade


def _profit_factor(gross_win: float, gross_loss: float) -> float:
    if gross_loss == 0.0:
        return math.inf if gross_win > 0.0 else 0.0
    return gross_win / gross_loss


def _max_drawdown(equity_curve: pd.Series) -> tuple[float, float]:
    if equity_curve.empty:
        return 0.0, 0.0
    running_max = equity_curve.cummax()
    drawdown = running_max - equity_curve
    max_dd = float(drawdown.max())
    if max_dd <= 0.0:
        return 0.0, 0.0
    peak = float(running_max.loc[drawdown.idxmax()])
    pct = max_dd / peak * 100.0 if peak > 0.0 else 0.0
    return max_dd, pct


def _longest_losing_streak(trades: list[Trade]) -> int:
    longest = 0
    current = 0
    for trade in trades:
        current = current + 1 if trade.pnl < 0.0 else 0
        longest = max(longest, current)
    return longest


def _return_pct(net_profit: float, initial_equity: float) -> float:
    return net_profit / initial_equity * 100.0 if initial_equity > 0.0 else 0.0


def _mean_r(trades: list[Trade]) -> float:
    return sum(trade.r_multiple for trade in trades) / len(trades) if trades else 0.0


def summarize(trades: list[Trade], equity_curve: pd.Series, initial_equity: float) -> dict:
    pnls = [trade.pnl for trade in trades]
    net_profit = float(sum(pnls))
    wins = sum(1 for pnl in pnls if pnl > 0.0)
    gross_win = float(sum(pnl for pnl in pnls if pnl > 0.0))
    gross_loss = float(-sum(pnl for pnl in pnls if pnl < 0.0))
    max_dd, max_dd_pct = _max_drawdown(equity_curve)
    return {
        "net_profit": net_profit,
        "return_pct": _return_pct(net_profit, initial_equity),
        "trades": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "win_rate": wins / len(trades) if trades else 0.0,
        "profit_factor": _profit_factor(gross_win, gross_loss),
        "expectancy_r": _mean_r(trades),
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "ambiguous_trades": sum(1 for trade in trades if trade.ambiguous),
        "longest_losing_streak": _longest_losing_streak(trades),
    }
