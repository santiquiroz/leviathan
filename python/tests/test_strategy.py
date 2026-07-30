from __future__ import annotations

import pandas as pd

from leviathan_bt.config import StrategyParams
from leviathan_bt.strategy import build_signals

_PARAMS = StrategyParams(
    ema_fast=2,
    ema_slow=3,
    ema_trend=4,
    structure_lookback=3,
    atr_period=3,
    swing_lookback=3,
)
_SIGNAL_ROW = 8


def _uptrend_frame() -> pd.DataFrame:
    # steady uptrend; row 7 is a small bearish bar, row 8 engulfs it and breaks structure
    rows = [
        (99.5, 100.2, 99.3, 100.0),
        (100.5, 101.2, 100.3, 101.0),
        (101.5, 102.2, 101.3, 102.0),
        (102.5, 103.2, 102.3, 103.0),
        (103.5, 104.2, 103.3, 104.0),
        (104.5, 105.2, 104.3, 105.0),
        (105.5, 106.2, 105.3, 106.0),
        (107.0, 107.1, 106.3, 106.4),
        (106.3, 108.2, 106.2, 108.0),
        (108.3, 108.8, 108.1, 108.6),
    ]
    index = pd.date_range("2024-01-01", periods=len(rows), freq="h")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=index)


def test_exactly_one_long_signal_at_engineered_row() -> None:
    signals = build_signals(_uptrend_frame(), _PARAMS)
    assert int(signals["long_signal"].sum()) == 1
    assert bool(signals["long_signal"].iloc[_SIGNAL_ROW])
    assert not signals["short_signal"].any()


def test_trend_column_is_bullish_after_first_bar() -> None:
    signals = build_signals(_uptrend_frame(), _PARAMS)
    assert int(signals["trend"].iloc[0]) == 0
    assert (signals["trend"].iloc[1:] == 1).all()


def test_pattern_column_labels_the_engulfing_signal() -> None:
    signals = build_signals(_uptrend_frame(), _PARAMS)
    assert signals["pattern"].iloc[_SIGNAL_ROW] == "engulfing"
    others = signals["pattern"].drop(signals.index[_SIGNAL_ROW])
    assert (others == "").all()
