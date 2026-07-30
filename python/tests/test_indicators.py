from __future__ import annotations

import math

import pandas as pd
import pytest

from leviathan_bt.indicators import atr, ema


def test_ema_matches_hand_computed_alpha_recursion() -> None:
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = ema(series, 3)
    # alpha = 2/(3+1) = 0.5: 1, 1.5, 2.25, 3.125, 4.0625
    assert result.tolist() == pytest.approx([1.0, 1.5, 2.25, 3.125, 4.0625])


def _atr_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0, 14.0, 15.0],
            "high": [12.0, 13.0, 15.0, 16.0, 20.0],
            "low": [9.0, 10.0, 11.0, 13.0, 14.0],
            "close": [11.0, 12.0, 14.0, 15.0, 18.0],
        }
    )


def test_atr_is_nan_before_seed_bar() -> None:
    result = atr(_atr_frame(), 3)
    assert result.iloc[:3].isna().all()


def test_atr_seed_matches_mt5_skipping_degenerate_first_tr() -> None:
    result = atr(_atr_frame(), 3)
    # true ranges: 3, 3, 4, 3, 6; MT5 seeds at index `period` with TR[1..3] -> 10/3
    assert result.iloc[3] == pytest.approx(10.0 / 3.0)


def test_atr_follows_wilder_recursion() -> None:
    result = atr(_atr_frame(), 3)
    # atr[4] = (10/3 * 2 + 6) / 3 = 38/9
    assert result.iloc[4] == pytest.approx(38.0 / 9.0)


def test_atr_returns_all_nan_when_frame_not_longer_than_period() -> None:
    result = atr(_atr_frame().iloc[:3], 3)
    assert result.isna().all()
