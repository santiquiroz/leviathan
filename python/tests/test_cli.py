from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from leviathan_bt.cli import main
from leviathan_bt.data import load_csv

_PYTHON_DIR = Path(__file__).resolve().parents[1]
_SAMPLE_MT5 = _PYTHON_DIR.parent / "data" / "sample" / "EURUSD_H1.csv"
_CONFIG = _PYTHON_DIR / "examples" / "config.example.toml"


def _write_binance_copy_of_sample(path: Path) -> Path:
    frame = load_csv(_SAMPLE_MT5)
    epochs_ms = (frame.index - pd.Timestamp(0)) // pd.Timedelta(milliseconds=1)
    klines = frame.assign(open_time=epochs_ms)[["open_time", "open", "high", "low", "close", "volume"]]
    klines.to_csv(path, header=False, index=False)
    return path


def _backtest_output(capsys: pytest.CaptureFixture[str], argv: list[str]) -> tuple[int, str]:
    code = main(argv)
    return code, capsys.readouterr().out


@pytest.mark.parametrize("extra_args", [[], ["--format", "binance"]])
def test_backtest_accepts_binance_klines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], extra_args: list[str]
) -> None:
    binance_path = _write_binance_copy_of_sample(tmp_path / "EURUSD_H1_binance.csv")
    mt5_argv = ["backtest", "--data", str(_SAMPLE_MT5), "--config", str(_CONFIG)]
    binance_argv = ["backtest", "--data", str(binance_path), "--config", str(_CONFIG), *extra_args]

    mt5_code, mt5_report = _backtest_output(capsys, mt5_argv)
    binance_code, binance_report = _backtest_output(capsys, binance_argv)

    assert (mt5_code, binance_code) == (0, 0)
    assert binance_report == mt5_report


def test_backtest_rejects_unknown_format(capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["backtest", "--data", str(_SAMPLE_MT5), "--config", str(_CONFIG), "--format", "parquet"]
    with pytest.raises(SystemExit):
        main(argv)
    assert "invalid choice" in capsys.readouterr().err


def test_backtest_prints_report_and_writes_it_to_out(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_path = tmp_path / "report.txt"
    argv = ["backtest", "--data", str(_SAMPLE_MT5), "--config", str(_CONFIG), "--out", str(out_path)]

    code, report = _backtest_output(capsys, argv)

    assert code == 0
    assert report.strip()
    assert out_path.read_text(encoding="utf-8") == report


def _write_grid(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_sweep_prints_ranked_table_with_grid_columns(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    grid = _write_grid(tmp_path / "grid.json", '{"risk_reward": [1.5, 2.0]}')
    argv = ["sweep", "--data", str(_SAMPLE_MT5), "--config", str(_CONFIG), "--grid", str(grid), "--jobs", "1"]

    code, table = _backtest_output(capsys, argv)

    header, *rows = table.strip().splitlines()
    assert code == 0
    assert header.split()[:2] == ["risk_reward", "net_profit"]
    assert "profit_factor" in header
    assert len(rows) == 2


def test_sweep_reports_when_no_combination_has_enough_trades(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # 60 bars cannot produce the default 30 trades
    short_data = tmp_path / "short.csv"
    short_data.write_text("\n".join(_SAMPLE_MT5.read_text(encoding="utf-8").splitlines()[:61]) + "\n", encoding="utf-8")
    grid = _write_grid(tmp_path / "grid.json", '{"risk_reward": [2.0]}')
    argv = ["sweep", "--data", str(short_data), "--config", str(_CONFIG), "--grid", str(grid), "--jobs", "1"]

    code, table = _backtest_output(capsys, argv)

    assert code == 0
    assert table.strip() == "no parameter set produced enough trades"


@pytest.mark.parametrize("content", ['[1.5, 2.0]', '{"risk_reward": 2.0}'])
def test_sweep_rejects_grid_that_is_not_an_object_of_lists(tmp_path: Path, content: str) -> None:
    grid = _write_grid(tmp_path / "grid.json", content)
    argv = ["sweep", "--data", str(_SAMPLE_MT5), "--config", str(_CONFIG), "--grid", str(grid), "--jobs", "1"]

    with pytest.raises(SystemExit, match="grid file must be a JSON object"):
        main(argv)


def test_missing_command_exits_with_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main([])
    assert raised.value.code == 2
    assert "usage" in capsys.readouterr().err
