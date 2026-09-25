from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from leviathan_bt import mcp_server  # noqa: E402
from leviathan_bt.config import load_toml  # noqa: E402
from leviathan_bt.data import load_csv  # noqa: E402
from leviathan_bt.sweep import run_full  # noqa: E402

_PYTHON_DIR = Path(__file__).resolve().parents[1]
_SAMPLE = _PYTHON_DIR.parent / "data" / "sample" / "EURUSD_H1.csv"
_CONFIG = _PYTHON_DIR / "examples" / "config.example.toml"

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


def _expected_run(**overrides):
    params, symbol, config = load_toml(_CONFIG)
    params = replace(params, **{k: v for k, v in overrides.items() if hasattr(params, k)})
    symbol = replace(symbol, **{k: v for k, v in overrides.items() if hasattr(symbol, k)})
    config = replace(config, **{k: v for k, v in overrides.items() if hasattr(config, k)})
    summary, trades, _ = run_full(load_csv(_SAMPLE), params, symbol, config)
    return json.loads(json.dumps(summary)), trades


def test_run_backtest_returns_summary_and_last_trades() -> None:
    expected_summary, trades = _expected_run()

    result = json.loads(mcp_server.leviathan_run_backtest(str(_SAMPLE), str(_CONFIG), last_trades=3))

    assert result["data"]["bars"] == 4000
    assert result["summary"] == expected_summary
    assert [row["entry_time"] for row in result["last_trades"]] == [str(t.entry_time) for t in trades[-3:]]
    assert {row["direction"] for row in result["last_trades"]} <= {"long", "short"}


def test_run_backtest_routes_overrides_to_strategy_symbol_and_backtest() -> None:
    overrides = {"risk_reward": 3.0, "spread_points": 15.0, "use_trailing": True}
    expected_summary, _ = _expected_run(**overrides)

    result = json.loads(mcp_server.leviathan_run_backtest(str(_SAMPLE), str(_CONFIG), overrides=overrides))

    assert result["summary"] == expected_summary
    assert result["summary"] != _expected_run()[0]


def test_run_backtest_rejects_unknown_override() -> None:
    with pytest.raises(ValueError, match="unknown override 'not_a_field'"):
        mcp_server.leviathan_run_backtest(str(_SAMPLE), overrides={"not_a_field": 1})


def test_walk_forward_tool_returns_rolling_steps() -> None:
    raw = mcp_server.leviathan_walk_forward(
        str(_SAMPLE), {"risk_reward": [1.5, 2.0]}, is_bars=1500, oos_bars=500, step_bars=500,
        config_path=str(_CONFIG),
    )

    result = json.loads(raw)
    assert len(result["steps"]) == 3
    assert set(result) == {"steps", "is_expectancy_r", "oos_expectancy_r", "wf_efficiency"}


def test_get_strategy_spec_returns_the_strategy_document() -> None:
    assert mcp_server.leviathan_get_strategy_spec().startswith("# Leviathan Strategy Specification")


_SIGNAL_LINES = [
    f"2024.01.0{day} 10:00;EURUSD;H1;{direction};engulfing;1.1;1.09;1.12;0.1"
    for day, direction in ((1, "long"), (2, "short"), (3, "long"))
]


def _signal_log(tmp_path: Path) -> Path:
    path = tmp_path / "Leviathan_signals.csv"
    path.write_text("\n".join(_SIGNAL_LINES) + "\n\n", encoding="utf-8")
    return path


def test_read_ea_signals_returns_the_last_rows_as_named_fields(tmp_path: Path) -> None:
    result = json.loads(mcp_server.leviathan_read_ea_signals(str(_signal_log(tmp_path)), last=2))

    assert result["total_signals"] == 3
    assert [row["time"] for row in result["last"]] == ["2024.01.02 10:00", "2024.01.03 10:00"]
    assert result["last"][0]["direction"] == "short"
    assert result["last"][0]["lots"] == "0.1"


def test_read_ea_signals_explains_how_to_enable_a_missing_log(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Log signals to file"):
        mcp_server.leviathan_read_ea_signals(str(tmp_path / "missing.csv"))
