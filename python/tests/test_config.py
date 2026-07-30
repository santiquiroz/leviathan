from __future__ import annotations

from pathlib import Path

from leviathan_bt.config import BacktestConfig, StrategyParams, SymbolSpec, load_toml

_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "config.example.toml"


def test_example_toml_round_trips_to_dataclass_defaults() -> None:
    params, symbol, config = load_toml(_EXAMPLE)
    assert params == StrategyParams()
    assert symbol == SymbolSpec()
    assert config == BacktestConfig()
