from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=2.0 / (period + 1.0), adjust=False).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    previous_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, period: int) -> pd.Series:
    # MT5 iATR: seed at index `period` with the SMA of TR[1..period] (skips the
    # degenerate TR[0] = high-low), then Wilder recursion
    tr = true_range(df).to_numpy(dtype=float)
    result = np.full(len(tr), np.nan)
    if len(tr) <= period:
        return pd.Series(result, index=df.index)
    result[period] = np.mean(tr[1 : period + 1])
    for i in range(period + 1, len(tr)):
        result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
    return pd.Series(result, index=df.index)
