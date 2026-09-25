from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pytest

from leviathan_bt.config import BacktestConfig, StrategyParams, SymbolSpec, load_toml

_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "config.example.toml"


def test_example_toml_round_trips_to_dataclass_defaults() -> None:
    params, symbol, config = load_toml(_EXAMPLE)
    assert params == StrategyParams()
    assert symbol == SymbolSpec()
    assert config == BacktestConfig()


@pytest.mark.parametrize(
    "overrides",
    [
        {"sl_mode": "ATR"},
        {"sl_mode": "fixed"},
        {"ema_fast": 0},
        {"ema_slow": -1},
        {"ema_trend": 0},
        {"structure_lookback": 0},
        {"atr_period": 0},
        {"swing_lookback": 0},
        {"pinbar_wick_ratio": 0.0},
        {"pinbar_wick_ratio": 1.0},
        {"pinbar_wick_ratio": math.nan},
        {"risk_reward": 0.0},
        {"risk_reward": -2.0},
    ],
)
def test_strategy_params_rejects_invalid_values(overrides: dict) -> None:
    with pytest.raises(ValueError, match=next(iter(overrides))):
        StrategyParams(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"point": 0.0},
        {"tick_size": 0.0},
        {"tick_size": -0.00001},
        {"lot_step": 0.0},
        {"lot_min": 1.0, "lot_max": 0.5},
    ],
)
def test_symbol_spec_rejects_invalid_values(overrides: dict) -> None:
    with pytest.raises(ValueError, match=next(iter(overrides))):
        SymbolSpec(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"sizing_mode": "risk%"},
        {"sizing_mode": "RISK_PERCENT"},
        {"initial_equity": 0.0},
        {"lot_size": 0.0},
        {"risk_percent": -1.0},
        {"session_start_hour": 24},
        {"session_start_hour": -1},
        {"session_end_hour": 24},
        {"session_end_hour": 7.5},
    ],
)
def test_backtest_config_rejects_invalid_values(overrides: dict) -> None:
    with pytest.raises(ValueError, match=next(iter(overrides))):
        BacktestConfig(**overrides)


@pytest.mark.parametrize(
    "build",
    [
        lambda: StrategyParams(sl_mode="swing", pinbar_wick_ratio=0.5),
        lambda: SymbolSpec(lot_min=0.5, lot_max=0.5),
        lambda: BacktestConfig(sizing_mode="risk_percent", session_start_hour=0, session_end_hour=23),
    ],
)
def test_valid_boundary_values_are_accepted(build) -> None:
    build()


def test_replace_revalidates_overrides() -> None:
    with pytest.raises(ValueError, match="atr_period"):
        replace(StrategyParams(), atr_period=0)


def test_load_toml_rejects_invalid_values(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text('[strategy]\nsl_mode = "ATR"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="sl_mode"):
        load_toml(path)
