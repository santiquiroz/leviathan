from __future__ import annotations

import numpy as np
import pandas as pd

from .config import StrategyParams
from .indicators import atr, ema
from .patterns import (
    bearish_engulfing,
    bearish_pinbar,
    bullish_engulfing,
    bullish_pinbar,
)
from .structure import bos_down, bos_up, swing_high, swing_low


def warmup_bars(params: StrategyParams) -> int:
    return max(params.ema_trend * 3, params.atr_period * 2, params.structure_lookback + 2)


def _trend(df: pd.DataFrame, params: StrategyParams) -> pd.Series:
    ema_fast = ema(df["close"], params.ema_fast)
    ema_slow = ema(df["close"], params.ema_slow)
    ema_trend = ema(df["close"], params.ema_trend)
    bullish = (ema_fast > ema_slow) & (df["close"] > ema_trend)
    bearish = (ema_fast < ema_slow) & (df["close"] < ema_trend)
    values = np.select([bullish, bearish], [1, -1], default=0)
    return pd.Series(values, index=df.index, dtype="int8")


def _disabled(df: pd.DataFrame) -> pd.Series:
    return pd.Series(False, index=df.index)


def _long_triggers(df: pd.DataFrame, params: StrategyParams) -> tuple[pd.Series, pd.Series]:
    engulfing = bullish_engulfing(df) if params.use_engulfing else _disabled(df)
    pinbar = bullish_pinbar(df, params.pinbar_wick_ratio) if params.use_pinbar else _disabled(df)
    return engulfing, pinbar


def _short_triggers(df: pd.DataFrame, params: StrategyParams) -> tuple[pd.Series, pd.Series]:
    engulfing = bearish_engulfing(df) if params.use_engulfing else _disabled(df)
    pinbar = bearish_pinbar(df, params.pinbar_wick_ratio) if params.use_pinbar else _disabled(df)
    return engulfing, pinbar


def _pattern_column(
    index: pd.Index,
    long_signal: pd.Series,
    short_signal: pd.Series,
    engulfing_long: pd.Series,
    engulfing_short: pd.Series,
) -> pd.Series:
    # engulfing-first priority per spec
    fired_engulfing = (long_signal & engulfing_long) | (short_signal & engulfing_short)
    fired_any = long_signal | short_signal
    labels = np.select([fired_engulfing, fired_any], ["engulfing", "pinbar"], default="")
    return pd.Series(labels, index=index)


def build_signals(df: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    trend = _trend(df, params)
    engulfing_long, pinbar_long = _long_triggers(df, params)
    engulfing_short, pinbar_short = _short_triggers(df, params)
    long_signal = (trend == 1) & bos_up(df, params.structure_lookback) & (engulfing_long | pinbar_long)
    short_signal = (trend == -1) & bos_down(df, params.structure_lookback) & (engulfing_short | pinbar_short)
    return pd.DataFrame(
        {
            "trend": trend,
            "long_signal": long_signal,
            "short_signal": short_signal,
            "atr": atr(df, params.atr_period),
            "swing_sl_long": swing_low(df, params.swing_lookback),
            "swing_sl_short": swing_high(df, params.swing_lookback),
            "pattern": _pattern_column(df.index, long_signal, short_signal, engulfing_long, engulfing_short),
        },
        index=df.index,
    )
