from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from leviathan_bt import mcp_server  # noqa: E402

_BINANCE_CONTENT = (
    "1704067200000,42000.0,42500.0,41800.0,42300.0,123.45\n"
    "1704070800000,42300.0,42600.0,42100.0,42500.0,98.7\n"
)


@pytest.mark.parametrize("data_format", ["auto", "binance"])
def test_describe_data_reads_binance_klines(tmp_path: Path, data_format: str) -> None:
    path = tmp_path / "binance.csv"
    path.write_text(_BINANCE_CONTENT, encoding="utf-8")

    described = json.loads(mcp_server.leviathan_describe_data(str(path), data_format=data_format))

    assert described["bars"] == 2
    assert described["start"] == "2024-01-01 00:00:00"
    assert described["close_max"] == pytest.approx(42500.0)
