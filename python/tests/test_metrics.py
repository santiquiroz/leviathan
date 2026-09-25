from __future__ import annotations

import math

import pandas as pd
import pytest

from leviathan_bt.engine import Trade
from leviathan_bt.metrics import summarize


def _trade(pnl: float, r_multiple: float = 0.0, ambiguous: bool = False) -> Trade:
    time = pd.Timestamp("2024-01-01")
    return Trade(
        entry_time=time,
        exit_time=time,
        direction=1,
        entry_price=1.0,
        exit_price=1.0,
        sl=0.9,
        tp=1.2,
        lots=0.1,
        pnl=pnl,
        r_multiple=r_multiple,
        exit_reason="tp" if pnl > 0.0 else "sl",
        ambiguous=ambiguous,
    )


def _curve(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="h"), dtype=float)


def test_no_trades_yields_zeroed_summary() -> None:
    summary = summarize([], _curve([1000.0, 1000.0]), 1000.0)
    assert summary["trades"] == 0
    assert summary["win_rate"] == 0.0
    assert summary["profit_factor"] == 0.0
    assert summary["expectancy_r"] == 0.0
    assert summary["longest_losing_streak"] == 0


def test_profit_factor_is_infinite_without_losing_trades() -> None:
    summary = summarize([_trade(10.0), _trade(5.0)], _curve([1000.0, 1015.0]), 1000.0)
    assert math.isinf(summary["profit_factor"])
    assert summary["losses"] == 0


def test_profit_factor_divides_gross_win_by_gross_loss() -> None:
    trades = [_trade(30.0), _trade(-10.0), _trade(-5.0)]
    summary = summarize(trades, _curve([1000.0, 1015.0]), 1000.0)
    assert summary["profit_factor"] == pytest.approx(2.0)


def test_counts_returns_and_expectancy() -> None:
    trades = [_trade(20.0, 2.0), _trade(-10.0, -1.0, ambiguous=True), _trade(0.0, 0.0)]
    summary = summarize(trades, _curve([1000.0, 1010.0]), 1000.0)
    assert summary["net_profit"] == pytest.approx(10.0)
    assert summary["return_pct"] == pytest.approx(1.0)
    assert (summary["trades"], summary["wins"], summary["losses"]) == (3, 1, 2)
    assert summary["win_rate"] == pytest.approx(1 / 3)
    assert summary["expectancy_r"] == pytest.approx(1 / 3)
    assert summary["ambiguous_trades"] == 1


def test_longest_losing_streak_resets_on_a_non_losing_trade() -> None:
    pnls = [-1.0, -1.0, 5.0, -1.0, -1.0, -1.0, 0.0, -1.0]
    summary = summarize([_trade(pnl) for pnl in pnls], _curve([1000.0]), 1000.0)
    assert summary["longest_losing_streak"] == 3


def test_max_drawdown_measures_the_deepest_fall_from_its_own_peak() -> None:
    # falls: 120 -> 90 (30, 25%) and 150 -> 125 (25, 16.7%)
    summary = summarize([], _curve([100.0, 120.0, 90.0, 150.0, 125.0, 160.0]), 100.0)
    assert summary["max_drawdown"] == pytest.approx(30.0)
    assert summary["max_drawdown_pct"] == pytest.approx(25.0)


@pytest.mark.parametrize("values", [[], [100.0, 110.0, 120.0]])
def test_max_drawdown_is_zero_for_empty_or_rising_curves(values: list[float]) -> None:
    summary = summarize([], _curve(values), 100.0)
    assert summary["max_drawdown"] == 0.0
    assert summary["max_drawdown_pct"] == 0.0
