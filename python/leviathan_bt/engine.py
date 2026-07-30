from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import BacktestConfig, StrategyParams, SymbolSpec
from .indicators import atr
from .strategy import warmup_bars


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: int
    entry_price: float
    exit_price: float
    sl: float
    tp: float
    lots: float
    pnl: float
    r_multiple: float
    exit_reason: str
    ambiguous: bool


@dataclass
class _Position:
    direction: int
    entry_time: pd.Timestamp
    entry_price: float
    sl: float
    tp: float
    initial_risk: float
    lots: float


def _bar_times(df: pd.DataFrame) -> pd.DatetimeIndex:
    if "time" in df.columns:
        return pd.DatetimeIndex(df["time"])
    return pd.DatetimeIndex(df.index)


def _atr_values(df: pd.DataFrame, signals: pd.DataFrame, params: StrategyParams) -> np.ndarray:
    # reuse the strategy's ATR when exposed so SL and trailing match signal generation exactly
    if "atr" in signals.columns:
        return signals["atr"].to_numpy(dtype=float)
    return atr(df, params.atr_period).to_numpy(dtype=float)


def _signal_direction(long_signal: bool, short_signal: bool) -> int:
    if long_signal:
        return 1
    if short_signal:
        return -1
    return 0


def _session_allows(hour: int, config: BacktestConfig) -> bool:
    if not config.use_session_filter:
        return True
    start, end = config.session_start_hour, config.session_end_hour
    if start == end:
        return True
    if start < end:
        return start <= hour < end
    # window crossing midnight, e.g. 22 -> 6
    return hour >= start or hour < end


def _entry_fill(direction: int, open_price: float, symbol: SymbolSpec) -> float:
    if direction == 1:
        return open_price + symbol.spread + symbol.slippage
    return open_price - symbol.slippage


def _entry_stop(
    direction: int, fill: float, atr_prev: float, swing_prev: float, params: StrategyParams
) -> float:
    if params.sl_mode == "atr":
        return fill - direction * atr_prev * params.atr_multiplier
    return swing_prev


def _stop_is_valid(direction: int, fill: float, sl: float) -> bool:
    if not math.isfinite(sl) or sl <= 0.0:
        return False
    return sl < fill if direction == 1 else sl > fill


def _take_profit(direction: int, fill: float, sl: float, risk_reward: float) -> float:
    return fill + direction * abs(fill - sl) * risk_reward


def _normalize_lots(lots: float, symbol: SymbolSpec) -> float:
    stepped = math.floor(round(lots / symbol.lot_step, 8)) * symbol.lot_step
    return min(max(round(stepped, 8), symbol.lot_min), symbol.lot_max)


def _position_lots(
    equity_now: float, sl_distance: float, symbol: SymbolSpec, config: BacktestConfig
) -> float:
    if config.sizing_mode == "risk_percent":
        risk_amount = equity_now * config.risk_percent / 100.0
        sl_points = sl_distance / symbol.point
        raw = risk_amount / (sl_points * symbol.point_value_per_lot())
    else:
        raw = config.lot_size
    return _normalize_lots(raw, symbol)


def _try_open(
    direction: int,
    open_price: float,
    atr_prev: float,
    swing_prev: float,
    entry_time: pd.Timestamp,
    equity_now: float,
    params: StrategyParams,
    symbol: SymbolSpec,
    config: BacktestConfig,
) -> _Position | None:
    fill = _entry_fill(direction, open_price, symbol)
    sl = _entry_stop(direction, fill, atr_prev, swing_prev, params)
    if not _stop_is_valid(direction, fill, sl):
        return None
    lots = _position_lots(equity_now, abs(fill - sl), symbol, config)
    if lots <= 0.0:
        return None
    return _Position(
        direction=direction,
        entry_time=entry_time,
        entry_price=fill,
        sl=sl,
        tp=_take_profit(direction, fill, sl, params.risk_reward),
        initial_risk=abs(fill - sl),
        lots=lots,
    )


def _apply_breakeven(
    position: _Position, high_prev: float, low_prev: float, symbol: SymbolSpec, config: BacktestConfig
) -> None:
    offset = config.breakeven_offset_points * symbol.point
    trigger = config.breakeven_trigger_r * position.initial_risk
    # simplification: triggers read bid highs/lows for both sides, ask adjustment for shorts is ignored
    if position.direction == 1:
        if high_prev >= position.entry_price + trigger and position.sl < position.entry_price:
            position.sl = position.entry_price + offset
        return
    if low_prev <= position.entry_price - trigger and position.sl > position.entry_price:
        position.sl = position.entry_price - offset


def _apply_trailing(
    position: _Position, close_prev: float, atr_prev: float, config: BacktestConfig
) -> None:
    if not math.isfinite(atr_prev):
        return
    distance = atr_prev * config.trailing_atr_mult
    if position.direction == 1:
        candidate = close_prev - distance
        if candidate > position.sl and candidate >= position.entry_price:
            position.sl = candidate
        return
    candidate = close_prev + distance
    if candidate < position.sl and candidate <= position.entry_price:
        position.sl = candidate


def _manage_position(
    position: _Position,
    high_prev: float,
    low_prev: float,
    close_prev: float,
    atr_prev: float,
    symbol: SymbolSpec,
    config: BacktestConfig,
) -> None:
    if config.use_breakeven:
        _apply_breakeven(position, high_prev, low_prev, symbol, config)
    if config.use_trailing:
        _apply_trailing(position, close_prev, atr_prev, config)


def _exit_on_bar(
    position: _Position, high: float, low: float, symbol: SymbolSpec
) -> tuple[float, str, bool] | None:
    if position.direction == 1:
        sl_hit = low <= position.sl
        tp_hit = high >= position.tp
    else:
        sl_hit = high + symbol.spread >= position.sl
        tp_hit = low + symbol.spread <= position.tp
    if sl_hit:
        # worst case when both levels are inside the bar: SL first, flagged ambiguous
        return position.sl - position.direction * symbol.slippage, "sl", bool(tp_hit)
    if tp_hit:
        return position.tp, "tp", False
    return None


def _end_fill(position: _Position, close_bid: float, symbol: SymbolSpec) -> float:
    # shorts buy back at ask
    return close_bid if position.direction == 1 else close_bid + symbol.spread


def _trade_pnl(position: _Position, exit_price: float, symbol: SymbolSpec) -> float:
    price_move = (exit_price - position.entry_price) * position.direction
    gross = price_move / symbol.point * symbol.point_value_per_lot() * position.lots
    commission = symbol.commission_per_lot * position.lots * 2.0
    return gross - commission


def _r_multiple(position: _Position, pnl: float, symbol: SymbolSpec) -> float:
    risk_points = position.initial_risk / symbol.point
    risk_value = risk_points * symbol.point_value_per_lot() * position.lots
    return pnl / risk_value if risk_value > 0.0 else 0.0


def _close_position(
    position: _Position,
    exit_time: pd.Timestamp,
    exit_price: float,
    reason: str,
    ambiguous: bool,
    symbol: SymbolSpec,
) -> Trade:
    pnl = _trade_pnl(position, exit_price, symbol)
    return Trade(
        entry_time=position.entry_time,
        exit_time=exit_time,
        direction=position.direction,
        entry_price=position.entry_price,
        exit_price=exit_price,
        sl=position.sl,
        tp=position.tp,
        lots=position.lots,
        pnl=pnl,
        r_multiple=_r_multiple(position, pnl, symbol),
        exit_reason=reason,
        ambiguous=ambiguous,
    )


def _floating_pnl(position: _Position | None, close_bid: float, symbol: SymbolSpec) -> float:
    if position is None:
        return 0.0
    mark = close_bid if position.direction == 1 else close_bid + symbol.spread
    price_move = (mark - position.entry_price) * position.direction
    return price_move / symbol.point * symbol.point_value_per_lot() * position.lots


def run_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    params: StrategyParams,
    symbol: SymbolSpec,
    config: BacktestConfig,
) -> tuple[list[Trade], pd.Series]:
    opens = df["open"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    times = _bar_times(df)
    atr_values = _atr_values(df, signals, params)
    long_signals = signals["long_signal"].to_numpy(dtype=bool)
    short_signals = signals["short_signal"].to_numpy(dtype=bool)
    swing_longs = signals["swing_sl_long"].to_numpy(dtype=float)
    swing_shorts = signals["swing_sl_short"].to_numpy(dtype=float)

    # entry reads signals at i-1, so at least one closed bar is required
    start = max(warmup_bars(params), 1)
    last = len(df) - 1
    equity = np.full(len(df), config.initial_equity, dtype=float)
    trades: list[Trade] = []
    if not config.one_position_only:
        # concurrent positions are unsupported here; failing fast beats silently
        # diverging from an EA run with InpOnePositionOnly=false
        raise ValueError("one_position_only=False is not supported by the Python engine")

    realized = config.initial_equity
    position: _Position | None = None

    for i in range(start, len(df)):
        if position is None:
            # single-position engine: signals while a position is open are ignored
            # regardless of config.one_position_only (concurrent positions unsupported)
            direction = _signal_direction(long_signals[i - 1], short_signals[i - 1])
            if direction != 0 and _session_allows(times[i].hour, config):
                swing_prev = swing_longs[i - 1] if direction == 1 else swing_shorts[i - 1]
                position = _try_open(
                    direction, opens[i], atr_values[i - 1], swing_prev,
                    times[i], realized, params, symbol, config,
                )
        else:
            # positions opened this bar are managed from the next bar, matching EA first-tick order
            _manage_position(
                position, highs[i - 1], lows[i - 1], closes[i - 1], atr_values[i - 1], symbol, config
            )
        if position is not None:
            hit = _exit_on_bar(position, highs[i], lows[i], symbol)
            if hit is not None:
                exit_price, reason, ambiguous = hit
                trade = _close_position(position, times[i], exit_price, reason, ambiguous, symbol)
                trades.append(trade)
                realized += trade.pnl
                position = None
        if position is not None and i == last:
            trade = _close_position(
                position, times[i], _end_fill(position, closes[i], symbol), "end", False, symbol
            )
            trades.append(trade)
            realized += trade.pnl
            position = None
        equity[i] = realized + _floating_pnl(position, closes[i], symbol)

    return trades, pd.Series(equity, index=df.index, name="equity")
