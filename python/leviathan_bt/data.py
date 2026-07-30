from __future__ import annotations

from pathlib import Path

import pandas as pd

_PRICE_COLUMNS = ("open", "high", "low", "close")
_VOLUME_ALIASES = ("volume", "tickvol", "vol")
_EPOCH_UNITS = ((1e17, "ns"), (1e14, "us"), (1e11, "ms"))


def load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    raw = pd.read_csv(file_path, sep=_sniff_separator(file_path), encoding="utf-8-sig")
    raw.columns = [_normalize_header(name) for name in raw.columns]
    return _to_canonical(raw, _mt5_timestamps(raw))


def load_binance_csv(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path, header=None).iloc[:, :6].copy()
    raw.columns = ["open_time", "open", "high", "low", "close", "volume"]
    epochs = pd.to_numeric(raw["open_time"], errors="coerce")
    rows = raw[epochs.notna()]  # drops a stray header row if the file has one
    stamps = epochs.dropna()
    timestamps = pd.to_datetime(stamps, unit=_epoch_unit(float(stamps.iloc[0])))
    return _to_canonical(rows, timestamps)


def load_yfinance(symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    try:
        import yfinance
    except ImportError as error:
        raise RuntimeError('pip install "leviathan-bt[data]"') from error
    raw = yfinance.download(
        symbol, start=start, end=end, interval=interval, auto_adjust=False, progress=False
    )
    return _from_yfinance(raw)


def _from_yfinance(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame.columns = [str(name).lower() for name in frame.columns]
    return _to_canonical(frame, pd.Series(frame.index))


def _sniff_separator(path: Path) -> str:
    with open(path, encoding="utf-8-sig") as handle:
        first_line = handle.readline()
    return "\t" if "\t" in first_line else ","


def _normalize_header(name: str) -> str:
    return str(name).strip().strip("<>").lower()


def _mt5_timestamps(raw: pd.DataFrame) -> pd.Series:
    # MT5 dates use dots (2024.01.15); dashes parse everywhere
    return pd.to_datetime(_timestamp_text(raw).str.replace(".", "-", regex=False))


def _timestamp_text(raw: pd.DataFrame) -> pd.Series:
    if "date" in raw.columns and "time" in raw.columns:
        return raw["date"].astype(str) + " " + raw["time"].astype(str)
    for name in ("date", "datetime", "time"):
        if name in raw.columns:
            return raw[name].astype(str)
    raise ValueError("no date/time column found in CSV header")


def _epoch_unit(sample: float) -> str:
    for threshold, unit in _EPOCH_UNITS:
        if sample >= threshold:
            return unit
    return "s"


def _volume_column(raw: pd.DataFrame) -> pd.Series:
    for name in _VOLUME_ALIASES:
        if name in raw.columns:
            return raw[name]
    return pd.Series(0.0, index=raw.index)


def _naive_utc_index(timestamps: pd.Series) -> pd.DatetimeIndex:
    index = pd.DatetimeIndex(timestamps)
    if index.tz is not None:
        index = index.tz_convert("UTC").tz_localize(None)
    return index.rename("time")


def _to_canonical(raw: pd.DataFrame, timestamps: pd.Series) -> pd.DataFrame:
    missing = [name for name in _PRICE_COLUMNS if name not in raw.columns]
    if missing:
        raise ValueError(f"missing price columns: {missing}")
    frame = pd.DataFrame({name: pd.to_numeric(raw[name], errors="coerce") for name in _PRICE_COLUMNS})
    frame["volume"] = pd.to_numeric(_volume_column(raw), errors="coerce").fillna(0.0)
    frame.index = _naive_utc_index(timestamps)
    cleaned = frame.dropna(subset=list(_PRICE_COLUMNS))
    deduped = cleaned[~cleaned.index.duplicated(keep="first")]
    return deduped.sort_index().astype(float)
