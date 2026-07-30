# Leviathan Strategy Specification

This document is the single source of truth for the trading logic. Both implementations (the MQL5 Expert Advisor and the Python backtester) MUST follow these rules exactly. Any behavioral difference between the two is a bug.

## Concept

Leviathan is a **trend-filtered price action** strategy. It only takes trades when three independent conditions align on the last **closed** candle:

1. **Trend filter (EMAs)** — the market is trending in the trade direction.
2. **Break of Structure (BOS)** — price has just broken a recent swing level.
3. **Entry trigger (candle pattern)** — a bullish/bearish engulfing or pinbar confirms momentum.

Risk is defined by an ATR-based or structure-based stop loss and a fixed risk:reward take profit.

## Bar indexing convention

MetaTrader convention is used everywhere:

- Bar `0` = the current, still-forming candle. **Never used for signals.**
- Bar `1` = the last closed candle. All signal logic reads bar `1` and older.
- Signals are evaluated **once per bar**, on the first tick after a new bar opens.

This eliminates repainting and lookahead bias by construction.

## Definitions

Let `open[i]`, `high[i]`, `low[i]`, `close[i]` be OHLC of bar `i` (MT5 indexing above).

### 1. Trend filter

Three EMAs on close price: `emaFast` (default 9), `emaSlow` (default 21), `emaTrend` (default 200). All read at bar `1`.

- **Bullish trend**: `emaFast[1] > emaSlow[1]` AND `close[1] > emaTrend[1]`
- **Bearish trend**: `emaFast[1] < emaSlow[1]` AND `close[1] < emaTrend[1]`
- Otherwise: **neutral** — no trades.

### 2. Break of Structure (BOS)

Structure lookback `N` (default 20), evaluated over bars `2 .. N+1` (i.e., excluding the signal bar itself):

- `swingHigh = max(high[2..N+1])`, `swingLow = min(low[2..N+1])`
- **Bullish BOS**: `close[1] > swingHigh`
- **Bearish BOS**: `close[1] < swingLow`

### 3. Entry triggers (candle patterns)

Evaluated on bar `1` (and bar `2` for engulfing). Patterns are checked in this priority order — **engulfing first, then pinbar** (first enabled match wins):

**Bullish engulfing** (body engulf):
- Bar 2 bearish: `close[2] < open[2]`
- Bar 1 bullish: `close[1] > open[1]`
- Body engulfs: `close[1] >= open[2]` AND `open[1] <= close[2]`

**Bearish engulfing** (mirror):
- Bar 2 bullish, bar 1 bearish, `open[1] >= close[2]` AND `close[1] <= open[2]`

**Bullish pinbar** (wick ratio `w`, default 0.66):
- `range = high[1] - low[1] > 0`
- `lowerWick = min(open[1], close[1]) - low[1]`
- `upperWick = high[1] - max(open[1], close[1])`
- Signal: `lowerWick / range >= w` AND `upperWick / range <= (1 - w) * 0.5`

**Bearish pinbar** (mirror): swap upper/lower wick roles.

### 4. Signal

- **Long signal**: bullish trend AND bullish BOS AND (bullish engulfing OR bullish pinbar).
- **Short signal**: bearish trend AND bearish BOS AND (bearish engulfing OR bearish pinbar).

### 5. Entry, Stop Loss, Take Profit

- **Entry**: market order at current ask (long) / bid (short) on the tick that produced the signal.
- **Stop loss**, two modes:
  - `ATR` mode (default): `SL = entry ∓ ATR(atrPeriod)[1] * atrMultiplier` (period 14, multiplier 1.5).
  - `Swing` mode: `SL = min(low[2..swingLookback+1])` for longs / `max(high[...])` for shorts (lookback default 10).
- **Take profit**: `TP = entry ± |entry - SL| * riskReward` (default 2.0).
- If the computed SL is invalid (zero, or on the wrong side of entry), the signal is discarded.

### 6. Position management

- Optional **one position at a time** (default on): no new entries while a Leviathan position is open on the symbol. The Python engine only supports this mode and fails fast if it is disabled; the EA supports both.
- Position size, two modes:
  - **Fixed lot** (default 0.10).
  - **Risk %**: lots sized so that `|entry - SL|` equals the configured % of account equity, normalized to the symbol's volume step and min/max bounds.
- Optional **break-even**: when price reaches `+1R` (configurable R multiple), move SL to entry (+ optional offset).
- Optional **ATR trailing stop**: candidate SL = `price ∓ ATR * trailMultiplier`. Applied only when the candidate is tighter than the current SL AND at or beyond the entry price (i.e., only once the position is in profit by at least the trail distance). Never loosens.

### 7. Filters (all optional)

- **Session filter**: only take signals between configured start/end hours (server time). Windows crossing midnight are supported (`start > end`). `start == end` means no restriction.
- **Max spread filter**: skip signals when current spread exceeds a configured limit in points.

### 8. Operating modes (EA only)

- **Signals-only (default)**: the EA draws the setup (arrow + entry/SL/TP lines), shows it on the panel, and sends alerts (popup / push / email). No orders are sent. The human decides.
- **Auto-trading (opt-in)**: the EA additionally executes the trade with the configured sizing.

## Default parameters

| Parameter | Default | Meaning |
|---|---|---|
| `riskReward` | 2.0 | TP distance as multiple of SL distance |
| `lotSize` | 0.10 | Fixed lot (when risk % sizing off) |
| `riskPercent` | 1.0 | Equity % risked per trade (when risk sizing on) |
| `useATRForSL` | true | ATR SL mode vs swing SL mode |
| `atrPeriod` | 14 | ATR period |
| `atrMultiplier` | 1.5 | ATR multiplier for SL |
| `swingLookback` | 10 | Bars for swing SL |
| `emaFast` | 9 | Fast EMA period |
| `emaSlow` | 21 | Slow EMA period |
| `emaTrend` | 200 | Macro trend EMA period |
| `structureLookback` | 20 | Bars for BOS detection |
| `useEngulfing` | true | Enable engulfing trigger |
| `usePinbar` | true | Enable pinbar trigger |
| `pinbarWickRatio` | 0.66 | Min dominant wick fraction of range |
| `onePositionOnly` | true | Single concurrent position |

## Backtesting semantics (Python engine contract)

The Python backtester is an **event-driven bar loop** that reproduces MT5 "Open Prices Only" semantics plus high/low SL/TP checks:

- Iterate bars `i` (chronological). Decide using data up to and including bar `i-1` only. Bar `i-1` is the EA's "bar 1".
- **Entry fill**: `open[i] + spread` for longs (ask), `open[i]` for shorts (bid = chart price). Chart bars are bid-based.
- **SL/TP checks** (per bar, while position open): longs exit on bid (`low[i] <= SL` → SL; `high[i] >= TP` → TP); shorts exit on ask (`high[i] + spread >= SL` → SL; `low[i] + spread <= TP` → TP).
- **Same-bar ambiguity**: if a single bar's range covers both SL and TP, assume **SL first** (worst case). The engine counts and reports ambiguous bars.
- **Indicators**: EMA = standard exponential (`alpha = 2/(n+1)`). ATR = Wilder smoothing seeded exactly like MT5 `iATR`: first value at index `period` = SMA of `TR[1..period]` (the degenerate `TR[0] = high-low` is excluded), then `atr[i] = (atr[i-1]*(period-1) + TR[i]) / period`.
- **Warm-up**: no trades until all indicators have valid values (`max(emaTrend, structureLookback+1, atrPeriod)` bars, plus EMA convergence margin).
- **Sizing**: lots floored to `lot_step`, clamped to broker min/max — matching EA rounding so trade-by-trade P&L is comparable.
- **Costs**: per-symbol config: spread (points), slippage (points, applied to market entries and SL exits, not TP), commission per lot per side.
- **Data schema**: UTC timestamps, columns `time, open, high, low, close, volume`. Loaders must document source timezone shifts (broker time is usually GMT+2/+3).

## Honest expectations

This is an educational reference implementation of a popular retail price-action recipe. **It is not a money printer.** Edge, if any, is regime-dependent and highly sensitive to spread, session and market. Backtest it yourself, walk it forward, and assume the default parameters are a starting point — not an answer.
