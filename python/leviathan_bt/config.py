from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import NoReturn

SL_MODES = ("atr", "swing")
SIZING_MODES = ("fixed_lot", "risk_percent")
_HOURS = range(24)


def _fail(owner: object, name: str, requirement: str) -> NoReturn:
    value = getattr(owner, name)
    raise ValueError(f"{type(owner).__name__}.{name} must be {requirement}, got {value!r}")


def _check_choice(owner: object, name: str, choices: tuple[str, ...]) -> None:
    if getattr(owner, name) not in choices:
        _fail(owner, name, f"one of {choices}")


def _check_positive(owner: object, *names: str) -> None:
    for name in names:
        # `not > 0` also rejects NaN
        if not getattr(owner, name) > 0:
            _fail(owner, name, "> 0")


def _check_open_unit_interval(owner: object, name: str) -> None:
    if not 0 < getattr(owner, name) < 1:
        _fail(owner, name, "strictly between 0 and 1")


def _check_hour(owner: object, *names: str) -> None:
    for name in names:
        if getattr(owner, name) not in _HOURS:
            _fail(owner, name, "an hour in 0..23")


@dataclass(frozen=True)
class StrategyParams:
    ema_fast: int = 9
    ema_slow: int = 21
    ema_trend: int = 200
    structure_lookback: int = 20
    use_engulfing: bool = True
    use_pinbar: bool = True
    pinbar_wick_ratio: float = 0.66
    sl_mode: str = "atr"  # "atr" | "swing"
    atr_period: int = 14
    atr_multiplier: float = 1.5
    swing_lookback: int = 10
    risk_reward: float = 2.0

    def __post_init__(self) -> None:
        _check_choice(self, "sl_mode", SL_MODES)
        _check_positive(
            self, "ema_fast", "ema_slow", "ema_trend", "structure_lookback", "atr_period", "swing_lookback"
        )
        _check_open_unit_interval(self, "pinbar_wick_ratio")
        _check_positive(self, "risk_reward")


@dataclass(frozen=True)
class SymbolSpec:
    name: str = "EURUSD"
    digits: int = 5
    point: float = 0.00001
    pip_size: float = 0.0001
    contract_size: float = 100_000.0
    spread_points: float = 10.0
    slippage_points: float = 2.0
    commission_per_lot: float = 0.0
    lot_step: float = 0.01
    lot_min: float = 0.01
    lot_max: float = 100.0
    tick_value: float = 1.0
    tick_size: float = 0.00001

    def __post_init__(self) -> None:
        _check_positive(self, "point", "tick_size", "lot_step")
        if not self.lot_min <= self.lot_max:
            _fail(self, "lot_min", f"<= lot_max ({self.lot_max!r})")

    @property
    def spread(self) -> float:
        return self.spread_points * self.point

    @property
    def slippage(self) -> float:
        return self.slippage_points * self.point

    def point_value_per_lot(self) -> float:
        return self.tick_value * (self.point / self.tick_size)


@dataclass(frozen=True)
class BacktestConfig:
    initial_equity: float = 10_000.0
    sizing_mode: str = "fixed_lot"  # "fixed_lot" | "risk_percent"
    lot_size: float = 0.10
    risk_percent: float = 1.0
    one_position_only: bool = True
    use_breakeven: bool = False
    breakeven_trigger_r: float = 1.0
    breakeven_offset_points: float = 0.0
    use_trailing: bool = False
    trailing_atr_mult: float = 2.0
    use_session_filter: bool = False
    session_start_hour: int = 7
    session_end_hour: int = 20

    def __post_init__(self) -> None:
        _check_choice(self, "sizing_mode", SIZING_MODES)
        _check_positive(self, "initial_equity", "lot_size", "risk_percent")
        _check_hour(self, "session_start_hour", "session_end_hour")


def _build(cls, section: dict):
    known = {f.name for f in fields(cls)}
    unknown = set(section) - known
    if unknown:
        raise ValueError(f"unknown {cls.__name__} keys: {sorted(unknown)}")
    return cls(**section)


def load_toml(path: str | Path) -> tuple[StrategyParams, SymbolSpec, BacktestConfig]:
    with open(path, "rb") as handle:
        raw = tomllib.load(handle)
    params = _build(StrategyParams, raw.get("strategy", {}))
    symbol = _build(SymbolSpec, raw.get("symbol", {}))
    config = _build(BacktestConfig, raw.get("backtest", {}))
    return params, symbol, config
