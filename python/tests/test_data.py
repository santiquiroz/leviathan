from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from leviathan_bt.data import load_any, load_binance_csv, load_csv

_CANONICAL_COLUMNS = ["open", "high", "low", "close", "volume"]


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_csv_mt5_angle_bracket_tab_format(tmp_path: Path) -> None:
    content = (
        "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
        "2024.01.15\t00:00:00\t1.09500\t1.09600\t1.09400\t1.09550\t1000\t0\t10\n"
        "2024.01.15\t01:00:00\t1.09550\t1.09650\t1.09450\t1.09600\t1100\t0\t10\n"
    )
    frame = load_csv(_write(tmp_path / "mt5.csv", content))
    assert list(frame.columns) == _CANONICAL_COLUMNS
    assert frame.index.name == "time"
    assert frame.index.tz is None
    assert frame.index.tolist() == [
        pd.Timestamp("2024-01-15 00:00:00"),
        pd.Timestamp("2024-01-15 01:00:00"),
    ]
    assert frame["open"].tolist() == pytest.approx([1.095, 1.0955])
    assert frame["close"].tolist() == pytest.approx([1.0955, 1.096])
    assert frame["volume"].tolist() == pytest.approx([1000.0, 1100.0])


def test_load_binance_csv_headerless_ms_epochs(tmp_path: Path) -> None:
    content = (
        "1704067200000,42000.0,42500.0,41800.0,42300.0,123.45\n"
        "1704070800000,42300.0,42600.0,42100.0,42500.0,98.7\n"
    )
    frame = load_binance_csv(_write(tmp_path / "binance.csv", content))
    assert list(frame.columns) == _CANONICAL_COLUMNS
    assert frame.index.name == "time"
    assert frame.index.tz is None
    assert frame.index.tolist() == [
        pd.Timestamp("2024-01-01 00:00:00"),
        pd.Timestamp("2024-01-01 01:00:00"),
    ]
    assert frame["close"].tolist() == pytest.approx([42300.0, 42500.0])
    assert frame["volume"].tolist() == pytest.approx([123.45, 98.7])


_MT5_CONTENT = (
    "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\n"
    "2024.01.15\t00:00:00\t1.09500\t1.09600\t1.09400\t1.09550\t1000\n"
    "2024.01.15\t01:00:00\t1.09550\t1.09650\t1.09450\t1.09600\t1100\n"
)
_BINANCE_CONTENT = (
    "1704067200000,42000.0,42500.0,41800.0,42300.0,123.45\n"
    "1704070800000,42300.0,42600.0,42100.0,42500.0,98.7\n"
)


def test_load_any_auto_detects_binance_klines(tmp_path: Path) -> None:
    path = _write(tmp_path / "binance.csv", _BINANCE_CONTENT)
    pd.testing.assert_frame_equal(load_any(path), load_binance_csv(path))


def test_load_any_auto_detects_mt5_export(tmp_path: Path) -> None:
    path = _write(tmp_path / "mt5.csv", _MT5_CONTENT)
    pd.testing.assert_frame_equal(load_any(path), load_csv(path))


def test_load_any_auto_detects_binance_with_header_row(tmp_path: Path) -> None:
    header = "open_time,open,high,low,close,volume,close_time\n"
    path = _write(tmp_path / "binance_header.csv", header + _BINANCE_CONTENT)
    pd.testing.assert_frame_equal(load_any(path), load_binance_csv(path))


def test_load_any_auto_detects_microsecond_binance_epochs(tmp_path: Path) -> None:
    content = "1735689600000000,94000.0,94500.0,93800.0,94300.0,12.5\n"
    frame = load_any(_write(tmp_path / "binance_us.csv", content))
    assert frame.index.tolist() == [pd.Timestamp("2025-01-01 00:00:00")]


@pytest.mark.parametrize(
    ("fmt", "content", "loader"),
    [("binance", _BINANCE_CONTENT, load_binance_csv), ("mt5", _MT5_CONTENT, load_csv)],
)
def test_load_any_explicit_format(tmp_path: Path, fmt: str, content: str, loader) -> None:
    path = _write(tmp_path / "data.csv", content)
    pd.testing.assert_frame_equal(load_any(path, fmt), loader(path))


def test_load_any_rejects_unknown_format(tmp_path: Path) -> None:
    path = _write(tmp_path / "binance.csv", _BINANCE_CONTENT)
    with pytest.raises(ValueError, match="unknown data format"):
        load_any(path, "parquet")
