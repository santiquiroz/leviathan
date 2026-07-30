from __future__ import annotations

import pandas as pd

from leviathan_bt.structure import bos_up, swing_high

_LOOKBACK = 3


def _frame(last_close: float) -> pd.DataFrame:
    rows = [
        (45.0, 50.0, 40.0, 45.0),
        (9.2, 10.0, 9.0, 9.5),
        (10.2, 11.0, 10.0, 10.5),
        (11.2, 12.0, 11.0, 11.5),
        (12.0, 100.0, 11.0, last_close),
    ]
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


def test_swing_high_window_ends_one_row_before_evaluated_row() -> None:
    swings = swing_high(_frame(12.5), _LOOKBACK)
    # row 4 window = highs of rows 1..3, excluding row 4's own high of 100
    assert swings.iloc[4] == 12.0
    # row 3 window still reaches row 0
    assert swings.iloc[3] == 50.0
    assert swings.iloc[:3].isna().all()


def test_bos_up_fires_when_close_exceeds_prior_window_max() -> None:
    result = bos_up(_frame(12.5), _LOOKBACK)
    # own high (100) is outside the window, so close 12.5 > 12.0 fires
    assert result.tolist() == [False, False, False, False, True]


def test_bos_up_silent_when_close_below_prior_window_max() -> None:
    result = bos_up(_frame(11.95), _LOOKBACK)
    # 11.95 < 12.0 (row 3 high, inside the window) -> no break anywhere
    assert result.tolist() == [False, False, False, False, False]
