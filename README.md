# 🐙 Leviathan

**English | [Español](README.es.md)**

Open-source, trend-filtered **price action trading bot** for MetaTrader 5, with a faithful Python backtesting engine.

> ## ⚠️ Disclaimer
>
> This software is for **educational purposes only**. It is not financial advice. Do not risk money you cannot afford to lose. **USE AT YOUR OWN RISK — the authors assume no responsibility for your trading results.** Always test on a demo account (MT5 Strategy Tester / Python backtests) before ever considering real money. Trading leveraged instruments carries a high risk of losing your entire capital.

## What it does

Leviathan trades (or just *signals* — that's the default) a classic retail price-action recipe, only when three independent conditions align on the last **closed** candle:

1. **Trend filter** — EMA(9) above EMA(21) and price above EMA(200) for longs (mirror for shorts).
2. **Break of Structure** — the close breaks the highest high / lowest low of the last 20 bars.
3. **Candle trigger** — a bullish/bearish **engulfing** or **pinbar** confirms momentum.

Stops come from ATR (or swing structure), targets from a fixed risk:reward ratio. Everything is a configurable input.

The full ruleset, with exact formulas shared by both implementations, lives in [docs/STRATEGY.md](docs/STRATEGY.md).

## Two implementations, one spec

| | MQL5 Expert Advisor | Python backtester |
|---|---|---|
| Purpose | Live signals / trading + MT5 Strategy Tester | Research: backtests, parameter sweeps, walk-forward |
| Location | [`mql5/`](mql5/) | [`python/`](python/) |
| Dependencies | MetaTrader 5 only | pandas + numpy (matplotlib optional) |
| Default mode | **Signals-only** (alerts, panel, no orders) | — |

Both follow `docs/STRATEGY.md` to the letter; any behavioral difference between them is a bug — please report it.

## Quickstart — MQL5 EA

1. Copy the contents of `mql5/` into your MetaTrader 5 data folder (`File → Open Data Folder → MQL5`):
   - `mql5/Experts/Leviathan.mq5` → `MQL5/Experts/`
   - `mql5/Include/Leviathan/` → `MQL5/Include/Leviathan/`
2. Compile `Leviathan.mq5` in MetaEditor (F7).
3. Drag the EA onto a chart. By default it runs **signals-only**: it draws the setup (arrow + entry/SL/TP lines), updates the chart panel, and sends popup/push/email alerts. You decide whether to take the trade.
4. To let it trade on its own, set `Operating mode` to `Auto-trading` — after you have backtested it and understood the risk.

## Quickstart — Python backtester

```bash
cd python
python -m venv .venv
source .venv/Scripts/activate   # Windows cmd: .venv\Scripts\activate.bat | Linux/macOS: source .venv/bin/activate
pip install -e .
leviathan-bt backtest --data ../data/sample/EURUSD_H1.csv --config examples/config.example.toml
```

Parameter sweep and walk-forward:

```bash
leviathan-bt sweep --data your_data.csv --config examples/config.example.toml --grid grid.json
```

Data sources (see loaders in `python/leviathan_bt/data.py`):
- **MT5 export** (highest fidelity — same broker feed as the EA): open a chart, `Ctrl+S` or use the terminal's export, then `load_csv`.
- **Binance Vision** kline CSVs for crypto.
- **yfinance** for quick daily-bar demos (`pip install -e .[data]` from `python/`).

## Configuration

All strategy parameters are exposed as EA inputs and TOML config keys. The main ones:

| Parameter | Default | Meaning |
|---|---|---|
| `riskReward` | 2.0 | TP distance as multiple of SL distance |
| `slMode` | ATR | `ATR` or `Swing` stop placement |
| `atrPeriod` / `atrMultiplier` | 14 / 1.5 | ATR stop settings |
| `emaFast` / `emaSlow` / `emaTrend` | 9 / 21 / 200 | Trend filter EMAs |
| `structureLookback` | 20 | Bars for Break of Structure |
| `useEngulfing` / `usePinbar` | true / true | Entry triggers |
| `pinbarWickRatio` | 0.66 | Min dominant wick fraction |
| `sizingMode` | Fixed lot | `Fixed lot` or `Risk %` of equity |
| `onePositionOnly` | true | Single concurrent position |

Extras (all off by default): break-even at +1R, ATR trailing stop and session filter (EA + backtester); max-spread filter and daily loss limit (EA only, auto mode).

The full table with every input is in [docs/STRATEGY.md](docs/STRATEGY.md).

## Honest expectations

Read this before dreaming: peer-reviewed research (Marshall, Young & Rose 2006, *Journal of Banking & Finance*) found **no significant predictive value in raw candlestick patterns**. Community backtests put EMA-crossover systems at a positive expectancy in only ~8 of 12 asset/timeframe combos — they work in trending regimes and bleed in ranges. At a fixed 1:2 R:R the mathematical breakeven is a 33.3% win rate *before* costs, and spread alone can eat 5–20% of risk per trade on tight intraday stops.

Leviathan ships honest defaults, not fitted ones. Treat it as a **framework to test ideas rigorously**, not a profit machine. The backtester deliberately models spread, slippage, commissions and worst-case same-bar fills so your results err on the conservative side.

## Repository layout

```
mql5/
  Experts/Leviathan.mq5          # thin orchestrator (OnInit/OnTick/OnDeinit)
  Include/Leviathan/*.mqh        # Signals, Risk, TradeManager, Filters, Broker, Alerts, Panel
python/
  leviathan_bt/                  # backtesting package (engine, indicators, patterns, sweep, cli)
  tests/                         # pytest suite
  examples/config.example.toml
docs/STRATEGY.md                 # THE spec — single source of truth for both implementations
```

## Contributing

PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Strategy-logic changes must update `docs/STRATEGY.md` in the same PR. New entry triggers (patterns), filters and data loaders are great first contributions.

## Credits

The strategy concept (EMA trend filter + break of structure + engulfing/pinbar entries) is a widely taught retail price-action recipe; this project is an independent, from-scratch open-source implementation of that public concept. No third-party code was used.

## License

[MIT](LICENSE)
