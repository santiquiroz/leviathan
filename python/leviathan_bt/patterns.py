from __future__ import annotations

import numpy as np
import pandas as pd


def bullish_engulfing(df: pd.DataFrame) -> pd.Series:
    prev_open = df["open"].shift(1)
    prev_close = df["close"].shift(1)
    prev_bearish = prev_close < prev_open
    current_bullish = df["close"] > df["open"]
    body_engulfs = (df["close"] >= prev_open) & (df["open"] <= prev_close)
    return prev_bearish & current_bullish & body_engulfs


def bearish_engulfing(df: pd.DataFrame) -> pd.Series:
    prev_open = df["open"].shift(1)
    prev_close = df["close"].shift(1)
    prev_bullish = prev_close > prev_open
    current_bearish = df["close"] < df["open"]
    body_engulfs = (df["open"] >= prev_close) & (df["close"] <= prev_open)
    return prev_bullish & current_bearish & body_engulfs


def _wick_fractions(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    body_low = np.minimum(df["open"], df["close"])
    body_high = np.maximum(df["open"], df["close"])
    bar_range = df["high"] - df["low"]
    # zero-range bars become NaN so every comparison downstream is False
    safe_range = bar_range.where(bar_range > 0)
    lower_fraction = (body_low - df["low"]) / safe_range
    upper_fraction = (df["high"] - body_high) / safe_range
    return lower_fraction, upper_fraction


def bullish_pinbar(df: pd.DataFrame, wick_ratio: float) -> pd.Series:
    lower_fraction, upper_fraction = _wick_fractions(df)
    small_wick_cap = (1.0 - wick_ratio) * 0.5
    return (lower_fraction >= wick_ratio) & (upper_fraction <= small_wick_cap)


def bearish_pinbar(df: pd.DataFrame, wick_ratio: float) -> pd.Series:
    lower_fraction, upper_fraction = _wick_fractions(df)
    small_wick_cap = (1.0 - wick_ratio) * 0.5
    return (upper_fraction >= wick_ratio) & (lower_fraction <= small_wick_cap)
