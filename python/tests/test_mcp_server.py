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


def test_grid_search_reports_every_tested_combination(tmp_path: Path) -> None:
    path = tmp_path / "flat.csv"
    rows = [f"{1704067200000 + hour * 3_600_000},1.1,1.1005,1.0995,1.1,10.0" for hour in range(60)]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    grid = {"ema_trend": [1, 3], "atr_period": [1, 2, 3]}

    result = json.loads(mcp_server.leviathan_grid_search(str(path), grid, min_trades=1_000))

    assert result["tested"] == 6
    assert result["kept"] == 0
    assert result["top"] == []
