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
