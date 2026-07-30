from __future__ import annotations

import pandas as pd

# MT5 mapping: the closed bar (shift 1) is pandas row t, so the swing window at
# shifts 2..lookback+1 is rows [t-lookback .. t-1] = rolling(lookback) shifted by 1.


def swing_high(df: pd.DataFrame, lookback: int) -> pd.Series:
    return df["high"].rolling(lookback).max().shift(1)


def swing_low(df: pd.DataFrame, lookback: int) -> pd.Series:
    return df["low"].rolling(lookback).min().shift(1)


def bos_up(df: pd.DataFrame, lookback: int) -> pd.Series:
    return df["close"] > swing_high(df, lookback)


def bos_down(df: pd.DataFrame, lookback: int) -> pd.Series:
    return df["close"] < swing_low(df, lookback)
