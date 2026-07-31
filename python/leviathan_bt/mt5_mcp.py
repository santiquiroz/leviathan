from __future__ import annotations

import json
import os
from typing import Any

try:
    from mcp.server import MCPServer
    from mcp.types import ToolAnnotations
except ImportError as exc:  # pragma: no cover
    raise RuntimeError('MCP support requires: pip install "leviathan-bt[mcp]"') from exc

try:
    import MetaTrader5 as mt5
except ImportError as exc:  # pragma: no cover
    raise RuntimeError('Live bridge requires: pip install MetaTrader5 (Windows only)') from exc

mcp = MCPServer("leviathan_mt5_mcp")

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
TRADE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True)

MAGIC = 226701
_TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
}


def _connect() -> None:
    if not mt5.initialize():
        raise RuntimeError(f"could not attach to a running MetaTrader 5 terminal: {mt5.last_error()}")


def _trading_enabled() -> None:
    if os.environ.get("LEVIATHAN_ALLOW_TRADING") != "1":
        raise PermissionError(
            "Trade execution is disabled. Set LEVIATHAN_ALLOW_TRADING=1 in the MCP server environment "
            "to enable it. Read-only tools work without it."
        )
    account = mt5.account_info()
    if account is None:
        raise RuntimeError(f"no account connected: {mt5.last_error()}")
    is_demo = account.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
    if not is_demo and os.environ.get("LEVIATHAN_ALLOW_REAL") != "1":
        raise PermissionError(
            f"Account {account.login} is NOT a demo account. Refusing to trade real money. "
            "Set LEVIATHAN_ALLOW_REAL=1 only if you truly understand the risk."
        )


@mcp.tool(name="mt5_account_info", title="MT5 account snapshot", annotations=READ_ONLY)
def mt5_account_info() -> str:
    """Balance, equity, margin, currency, server and whether the connected MT5 account is demo or real."""
    _connect()
    account = mt5.account_info()
    if account is None:
        raise RuntimeError(f"no account connected: {mt5.last_error()}")
    return json.dumps(
        {
            "login": account.login,
            "server": account.server,
            "mode": "demo" if account.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else "REAL",
            "currency": account.currency,
            "balance": account.balance,
            "equity": account.equity,
            "margin_free": account.margin_free,
            "leverage": account.leverage,
        },
        indent=2,
    )


@mcp.tool(name="mt5_positions", title="Open positions", annotations=READ_ONLY)
def mt5_positions() -> str:
    """All open positions with entry, SL/TP and floating profit. Leviathan's own trades carry magic 226701."""
    _connect()
    positions = mt5.positions_get() or []
    rows = [
        {
            "ticket": p.ticket,
            "symbol": p.symbol,
            "direction": "long" if p.type == mt5.POSITION_TYPE_BUY else "short",
            "lots": p.volume,
            "entry": p.price_open,
            "sl": p.sl,
            "tp": p.tp,
            "profit": p.profit,
            "magic": p.magic,
            "is_leviathan": p.magic == MAGIC,
            "comment": p.comment,
        }
        for p in positions
    ]
    return json.dumps({"count": len(rows), "positions": rows}, indent=2)


@mcp.tool(name="mt5_quote", title="Current quote", annotations=READ_ONLY)
def mt5_quote(symbol: str) -> str:
    """Live bid/ask and spread in points for a symbol, e.g. EURUSD."""
    _connect()
    if not mt5.symbol_select(symbol, True):
        raise ValueError(f"unknown symbol '{symbol}': {mt5.last_error()}")
    tick = mt5.symbol_info_tick(symbol)
    info = mt5.symbol_info(symbol)
    if tick is None or info is None:
        raise RuntimeError(f"no tick data for {symbol}: {mt5.last_error()}")
    return json.dumps(
        {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "spread_points": round((tick.ask - tick.bid) / info.point, 1),
            "time": str(tick.time),
        },
        indent=2,
    )


@mcp.tool(name="mt5_recent_bars", title="Recent OHLC bars", annotations=READ_ONLY)
def mt5_recent_bars(symbol: str, timeframe: str = "H1", count: int = 100) -> str:
    """Last N bars (open/high/low/close/volume) straight from the broker feed. timeframe: M1..W1."""
    _connect()
    tf = _TIMEFRAMES.get(timeframe.upper())
    if tf is None:
        raise ValueError(f"timeframe must be one of {sorted(_TIMEFRAMES)}")
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, min(count, 1000))
    if rates is None:
        raise RuntimeError(f"no bars for {symbol} {timeframe}: {mt5.last_error()}")
    rows = [
        {"time": str(r["time"]), "open": float(r["open"]), "high": float(r["high"]),
         "low": float(r["low"]), "close": float(r["close"]), "volume": int(r["tick_volume"])}
        for r in rates
    ]
    return json.dumps({"symbol": symbol, "timeframe": timeframe.upper(), "bars": rows}, indent=2, default=str)


@mcp.tool(name="mt5_deal_history", title="Closed deal history", annotations=READ_ONLY)
def mt5_deal_history(days: int = 30) -> str:
    """Closed deals of the last N days: entries, exits and realized profit - the account's trading journal."""
    import datetime as dt

    _connect()
    now = dt.datetime.now()
    deals = mt5.history_deals_get(now - dt.timedelta(days=days), now) or []
    rows = [
        {
            "time": str(dt.datetime.fromtimestamp(d.time)),
            "symbol": d.symbol,
            "type": "buy" if d.type == mt5.DEAL_TYPE_BUY else "sell" if d.type == mt5.DEAL_TYPE_SELL else str(d.type),
            "lots": d.volume,
            "price": d.price,
            "profit": d.profit,
            "magic": d.magic,
            "comment": d.comment,
        }
        for d in deals
        if d.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL)
    ]
    return json.dumps({"days": days, "deals": rows}, indent=2)


@mcp.tool(name="mt5_place_order", title="Place a market order (gated)", annotations=TRADE)
def mt5_place_order(
    symbol: str,
    direction: str,
    lots: float,
    sl: float,
    tp: float,
    comment: str = "Leviathan-MCP",
) -> str:
    """Send a market order with mandatory SL/TP. DISABLED unless env LEVIATHAN_ALLOW_TRADING=1, and refuses
    real (non-demo) accounts unless LEVIATHAN_ALLOW_REAL=1 as well. direction: "long" | "short".
    """
    _connect()
    _trading_enabled()
    if direction not in ("long", "short"):
        raise ValueError('direction must be "long" or "short"')
    if sl <= 0 or tp <= 0:
        raise ValueError("sl and tp are mandatory - no naked positions via this tool")
    if not mt5.symbol_select(symbol, True):
        raise ValueError(f"unknown symbol '{symbol}'")
    tick = mt5.symbol_info_tick(symbol)
    price = tick.ask if direction == "long" else tick.bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lots,
        "type": mt5.ORDER_TYPE_BUY if direction == "long" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": MAGIC,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"order_send failed: {mt5.last_error()}")
    return json.dumps(
        {"retcode": result.retcode, "ok": result.retcode == mt5.TRADE_RETCODE_DONE,
         "order": result.order, "price": result.price, "comment": result.comment},
        indent=2,
    )


@mcp.tool(name="mt5_close_position", title="Close a position (gated)", annotations=TRADE)
def mt5_close_position(ticket: int) -> str:
    """Close an open position by ticket. Same gating as mt5_place_order (demo-only unless explicitly overridden)."""
    _connect()
    _trading_enabled()
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        raise ValueError(f"no open position with ticket {ticket}")
    p = positions[0]
    tick = mt5.symbol_info_tick(p.symbol)
    closing_type = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": p.symbol,
        "volume": p.volume,
        "type": closing_type,
        "price": tick.bid if closing_type == mt5.ORDER_TYPE_SELL else tick.ask,
        "deviation": 10,
        "magic": MAGIC,
        "comment": "Leviathan-MCP close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"order_send failed: {mt5.last_error()}")
    return json.dumps(
        {"retcode": result.retcode, "ok": result.retcode == mt5.TRADE_RETCODE_DONE, "closed": ticket},
        indent=2,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
