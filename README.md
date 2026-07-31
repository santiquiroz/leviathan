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

Already know MetaTrader? Four steps:

1. Copy the contents of `mql5/` into your MetaTrader 5 data folder (`File → Open Data Folder → MQL5`):
   - `mql5/Experts/Leviathan.mq5` → `MQL5/Experts/`
   - `mql5/Include/Leviathan/` → `MQL5/Include/Leviathan/`
2. Compile `Leviathan.mq5` in MetaEditor (F7).
3. Drag the EA onto a chart. By default it runs **signals-only**: it draws the setup (arrow + entry/SL/TP lines), updates the chart panel, and sends popup/push/email alerts. You decide whether to take the trade.
4. To let it trade on its own, set `Operating mode` to `Auto-trading` — after you have backtested it and understood the risk.

### Never used MetaTrader? Full walkthrough

**Phase 1 — Install (10 minutes, free, no real money):**

1. Download **MetaTrader 5** from metatrader5.com (or from your broker if you already have one).
2. Open it. On first launch it asks for an account: choose a **demo account** (the "MetaQuotes-Demo" server works). Fake money — this is how you test everything for weeks before even thinking about real funds.
3. `File → Open Data Folder`. A file explorer opens; go into the `MQL5` folder.
4. From this repo, copy:
   - `mql5/Experts/Leviathan.mq5` → into `MQL5/Experts/`
   - the whole `mql5/Include/Leviathan/` folder → into `MQL5/Include/`
5. Back in MT5 press **F4** (opens MetaEditor). Open `Experts/Leviathan.mq5` and press **F7** (compile). The log below must say `0 errors, 0 warnings` — that produces the executable `.ex5`.

**Phase 2 — Put it on a chart:**

6. Back in MT5, **Ctrl+N** opens the Navigator → `Expert Advisors → Leviathan`.
7. Drag "Leviathan" onto a chart, e.g. **EURUSD H1** (to change timeframe: right-click the chart → Timeframes → H1).
8. In the dialog that appears, "Common" tab: tick "Allow Algo Trading" and hit OK. The **dark panel** appears in the top-left corner.
9. That's it. Default mode = **signals-only**: the bot does NOT trade. When the three conditions align (trend + structure break + candle) it draws the arrow and Entry/SL/TP lines and fires an alert with the suggested lot size. You decide whether to enter manually.
10. Phone alerts: install the MT5 mobile app, then on desktop go to `Tools → Options → Notifications` and paste your MetaQuotes ID (the app shows it under Settings → Messages).

**Phase 3 — Backtest before believing anything:**

11. **Ctrl+R** opens the Strategy Tester: pick Leviathan, a symbol, a date range, model "Every tick based on real ticks", and press Start. Visual mode lets you watch the signals replay.
12. For serious research (parameter sweeps, walk-forward) use the Python engine below — the quickstart runs in three commands with the included sample data.

**Golden rule: at least 1–2 months on demo.** At 1:2 R:R you need a win rate above 33.3% just to break even *before* costs — see [Honest expectations](#honest-expectations).

### Using the EA day to day

- **Panel** (top-left): shows mode, trend (BULLISH/BEARISH/NEUTRAL), last signal, R:R and the suggested Entry/SL/TP of the latest setup. The bottom button pauses/resumes signal detection without removing the EA.
- **When a signal fires**: an arrow + dashed Entry/SL/TP lines appear on the chart and you get the alerts you enabled — `Terminal popup`, `Push notification` to the MT5 mobile app, `Email`, and/or a **webhook** (paste a Discord or Slack webhook URL into `Webhook URL` and whitelist it under `Tools → Options → Expert Advisors → Allow WebRequest`). In signals-only mode nothing is traded — the alert includes the suggested lot size so you can execute manually.
- **Signal log**: with `Log signals to file` on (default), every signal is appended to `MQL5/Files/Leviathan_signals.csv` — an auditable history you can analyze later (or feed to Claude via the MCP server below).
- **Auto-trading mode**: uses your sizing mode (`Fixed lot` or `Risk %` of equity), respects `Single concurrent position`, and applies the optional break-even / ATR trailing / session / spread / daily-loss-limit settings. One `Magic number` per chart if you run several instances.
- **Strategy Tester**: the EA runs in MT5's tester (Ctrl+R) — use "Every tick based on real ticks" for the most realistic fills, and the visual mode to watch the panel and signals replay.

### Prebuilt executable

A compiled `Leviathan.ex5` will be attached to [GitHub Releases](https://github.com/santiquiroz/leviathan/releases) soon, so non-programmers can drop it straight into `MQL5/Experts/` without opening MetaEditor. Until then, compiling from source takes about two minutes (steps above) — and compiling yourself is always the more trustworthy option for anything that can touch your money.

## Quickstart — Python backtester

```bash
cd python
python -m venv .venv
source .venv/Scripts/activate   # Windows cmd: .venv\Scripts\activate.bat | Linux/macOS: source .venv/bin/activate
pip install -e .
leviathan-bt backtest --data ../data/sample/EURUSD_H1.csv --config examples/config.example.toml
```

Useful flags: `--out report.txt` saves the text report, `--plot equity.png` saves the equity curve (needs `pip install -e .[plot]`).

**Parameter sweep** — put the values to test in a JSON file:

```json
{ "atr_multiplier": [1.0, 1.5, 2.0], "risk_reward": [1.5, 2.0, 3.0], "structure_lookback": [10, 20, 30] }
```

```bash
leviathan-bt sweep --data your_data.csv --config examples/config.example.toml --grid grid.json --jobs 4
```

Prints the top 10 combinations by profit factor (sets with fewer than 30 trades are dropped — too little evidence).

**Walk-forward** (the honest way to evaluate a sweep) — from Python:

```python
from leviathan_bt import load_csv, load_toml
from leviathan_bt.sweep import walk_forward

df = load_csv("your_data.csv")
params, symbol, config = load_toml("examples/config.example.toml")
result = walk_forward(df, params, {"atr_multiplier": [1.0, 1.5, 2.0]}, symbol, config,
                      is_bars=4000, oos_bars=1000, step_bars=1000)
print(result["wf_efficiency"])   # out-of-sample R / in-sample R — below ~0.5 smells like overfitting
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

## Claude / AI integration (MCP server)

Leviathan ships an [MCP](https://modelcontextprotocol.io) server so AI assistants (Claude Code, Claude Desktop, or any MCP client) can drive the backtester conversationally — "backtest this CSV with ATR 2.0", "sweep the RR from 1.5 to 3 and walk-forward the winner", "read my EA's signal log and compare it against the backtest".

```bash
cd python && pip install -e .[mcp]
claude mcp add leviathan -- leviathan-mcp        # Claude Code
```

Tools exposed (all read-only): `leviathan_run_backtest`, `leviathan_grid_search`, `leviathan_walk_forward`, `leviathan_describe_data`, `leviathan_get_strategy_spec`, `leviathan_read_ea_signals` (reads the EA's `Leviathan_signals.csv` log).

### Live terminal bridge (Windows)

A second MCP server connects to a **running MT5 terminal** through the official `MetaTrader5` package:

```bash
pip install -e .[mcp] MetaTrader5
claude mcp add leviathan-mt5 -- leviathan-mt5-mcp
```

Read-only tools: `mt5_account_info`, `mt5_positions`, `mt5_quote`, `mt5_recent_bars`, `mt5_deal_history`. Two **gated** execution tools (`mt5_place_order`, `mt5_close_position`) are disabled unless the server runs with `LEVIATHAN_ALLOW_TRADING=1` — and even then they refuse non-demo accounts unless `LEVIATHAN_ALLOW_REAL=1` is also set. Orders always require SL and TP.

Example prompts once connected: *"check my MT5 account and open positions"*, *"pull the last 200 H1 bars of EURUSD from the terminal and tell me if a Leviathan setup is close"*, *"read the EA's signal log, compare it with the deal history, and tell me which signals I skipped"*.

**On full automation**: if you want unattended execution, the EA's `Auto-trading` mode already does it — deterministic, on every tick, no AI in the loop. The Claude-in-the-loop pattern is best as a *supervisor*: reviewing signals, journaling trades, auditing whether live results match the backtest. An LLM deciding entries in real time adds latency and nondeterminism without adding edge.

A note on "AI models for trading", since it comes up: the evidence to date says zero-shot price-prediction models (time-series foundation models, FinBERT-style sentiment) do **not** provide an out-of-the-box edge — published evaluations show them underperforming plain gradient-boosting baselines on returns, and popular sentiment models scoring worse than random on next-day moves. Where AI demonstrably helps is as a **research copilot**: writing and auditing strategies, running honest backtests, catching overfitting. That is exactly the role this MCP server gives it.

## Why MetaTrader 5 — and when to use something else

MT5 is not vendor lock-in; it is the de-facto standard of retail forex. For what this bot does (forex/gold/indices, price-action signals, manual or semi-auto execution) it is the right tool: free, supported by nearly every broker, built-in tester with real ticks, push alerts to your phone, runs on a $5 VPS.

The real lock-in risk is already neutralized by design: the strategy lives in [docs/STRATEGY.md](docs/STRATEGY.md) (paper, not platform) and the Python engine is pure pandas — MT5 is just the execution adapter. Swapping platforms later means rewriting one thin layer, not the project.

When a different stack IS the better call:

- **Crypto** → [freqtrade](https://www.freqtrade.io) (open source, real exchanges, dry-run mode). Broker CFD crypto on MT5 has terrible spreads — don't force Leviathan there.
- **US stocks** → Interactive Brokers API.
- **Institutional-grade infrastructure** → [NautilusTrader](https://nautilustrader.io) — powerful, but the learning curve isn't justified for this strategy class.
- **What to avoid**: paid closed-source EAs and proprietary indicators from paid communities — *that* is real lock-in (to someone else's black box). This repo exists precisely so you don't depend on one.

## Popular strategy families — and where Leviathan fits

The most-used approaches in retail algo trading, for context:

| Family | Idea | Leviathan |
|---|---|---|
| **Trend following** | Trade in the direction of a moving-average / higher-timeframe trend | ✅ Core: EMA 9/21 + EMA 200 filter |
| **Breakout / structure** | Enter when price breaks a recent high/low or range | ✅ Core: Break of Structure trigger |
| **Candle-pattern confirmation** | Engulfing, pinbar, inside bar as entry timing | ✅ Core: engulfing + pinbar (more patterns = welcome PRs) |
| **Mean reversion** | Fade moves back to a mean (RSI extremes, Bollinger touches) | ❌ Opposite thesis — would fight the trend filter; fits better as a separate strategy module |
| **Momentum / MA crossover** | Enter on fast/slow crossover itself | Partial — Leviathan uses the crossover state as a *filter*, not as the entry |
| **Grid / DCA** | Ladder of orders around price, average down | ❌ Out of scope (the freqtrade/OctoBot crowd does this well for crypto) |
| **Scalping / HFT** | Many small trades on ticks/seconds | ❌ Out of scope — needs infrastructure this project deliberately avoids |

Leviathan is a **trend-following breakout system with candle-pattern confirmation** — the combination most retail price-action courses teach. That popularity is exactly why it deserves an honest, testable open-source implementation.

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
