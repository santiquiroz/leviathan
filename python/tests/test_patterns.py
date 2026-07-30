from __future__ import annotations

import pandas as pd

from leviathan_bt.patterns import (
    bearish_engulfing,
    bearish_pinbar,
    bullish_engulfing,
    bullish_pinbar,
)

_WICK_RATIO = 0.66


def _ohlc(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


def test_bullish_engulfing_positive() -> None:
    df = _ohlc(
        [
            (10.0, 10.2, 9.8, 10.1),
            (10.0, 10.1, 8.8, 9.0),
            (8.9, 10.3, 8.8, 10.1),
        ]
    )
    assert bool(bullish_engulfing(df).iloc[2])


def test_bullish_engulfing_negative_when_body_not_engulfed() -> None:
    df = _ohlc(
        [
            (10.0, 10.2, 9.8, 10.1),
            (10.0, 10.1, 8.8, 9.0),
            (9.2, 10.3, 9.1, 10.1),
        ]
    )
    # open[1] = 9.2 > close[2] = 9.0 breaks the engulf rule
    assert not bool(bullish_engulfing(df).iloc[2])


def test_bearish_engulfing_positive() -> None:
    df = _ohlc(
        [
            (10.0, 10.2, 9.8, 10.1),
            (9.0, 10.2, 8.9, 10.0),
            (10.1, 10.2, 8.7, 8.9),
        ]
    )
    assert bool(bearish_engulfing(df).iloc[2])


def test_bearish_engulfing_negative_when_body_not_engulfed() -> None:
    df = _ohlc(
        [
            (10.0, 10.2, 9.8, 10.1),
            (9.0, 10.2, 8.9, 10.0),
            (10.1, 10.2, 9.1, 9.2),
        ]
    )
    # close[1] = 9.2 > open[2] = 9.0 breaks the engulf rule
    assert not bool(bearish_engulfing(df).iloc[2])


def test_bullish_pinbar_fires_at_exact_wick_ratio_boundary() -> None:
    df = _ohlc(
        [
            (50.0, 60.0, 40.0, 55.0),
            (50.0, 60.0, 40.0, 45.0),
            (66.0, 100.0, 0.0, 84.0),
        ]
    )
    # lower wick 66/100 == 0.66 boundary, upper wick 16/100 within the small-wick cap
    assert bool(bullish_pinbar(df, _WICK_RATIO).iloc[2])


def test_bullish_pinbar_negative_just_below_wick_ratio() -> None:
    df = _ohlc(
        [
            (50.0, 60.0, 40.0, 55.0),
            (50.0, 60.0, 40.0, 45.0),
            (65.0, 100.0, 0.0, 84.0),
        ]
    )
    # lower wick 65/100 = 0.65 < 0.66
    assert not bool(bullish_pinbar(df, _WICK_RATIO).iloc[2])


def test_bearish_pinbar_fires_at_exact_wick_ratio_boundary() -> None:
    df = _ohlc(
        [
            (50.0, 60.0, 40.0, 55.0),
            (50.0, 60.0, 40.0, 45.0),
            (34.0, 100.0, 0.0, 16.0),
        ]
    )
    # upper wick 66/100 == 0.66 boundary, lower wick 16/100 within the small-wick cap
    assert bool(bearish_pinbar(df, _WICK_RATIO).iloc[2])


def test_bearish_pinbar_negative_just_below_wick_ratio() -> None:
    df = _ohlc(
        [
            (50.0, 60.0, 40.0, 55.0),
            (50.0, 60.0, 40.0, 45.0),
            (35.0, 100.0, 0.0, 16.0),
        ]
    )
    # upper wick 65/100 = 0.65 < 0.66
    assert not bool(bearish_pinbar(df, _WICK_RATIO).iloc[2])
