//+------------------------------------------------------------------+
//| Leviathan - TradeManager.mqh                                     |
//| Order execution and open-position management                     |
//+------------------------------------------------------------------+
#ifndef LEVIATHAN_TRADEMANAGER_MQH
#define LEVIATHAN_TRADEMANAGER_MQH

#include <Trade\Trade.mqh>
#include "Broker.mqh"
#include "Signals.mqh"

CTrade g_levTrade;
long   g_levMagic = 0;

bool LevTradeInit(const long magic, const int deviationPoints)
  {
   g_levMagic = magic;
   g_levTrade.SetExpertMagicNumber(magic);
   g_levTrade.SetDeviationInPoints(deviationPoints);
   return true;
  }

bool LevIsOwnPosition()
  {
   return PositionGetString(POSITION_SYMBOL) == _Symbol &&
          PositionGetInteger(POSITION_MAGIC) == g_levMagic;
  }

bool LevHasOpenPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0)
         continue;
      if(LevIsOwnPosition())
         return true;
     }
   return false;
  }

bool LevMarginAllows(const int direction, const double lots, const double price)
  {
   double margin = 0.0;
   ENUM_ORDER_TYPE type = direction > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!OrderCalcMargin(type, _Symbol, lots, price, margin))
      return false;
   return margin <= AccountInfoDouble(ACCOUNT_MARGIN_FREE);
  }

bool LevOpenPosition(const int direction, const double lots, const double sl, const double tp,
                     const string comment)
  {
   for(int attempt = 0; attempt < 3; attempt++)
     {
      MqlTick tick;
      if(!SymbolInfoTick(_Symbol, tick))
         return false;
      double price = direction > 0 ? tick.ask : tick.bid;

      if(!LevStopsValid(direction, price, sl, tp))
        {
         Print("Leviathan: SL/TP too close to price (broker stop level), order skipped.");
         return false;
        }
      if(!LevMarginAllows(direction, lots, price))
        {
         Print("Leviathan: insufficient free margin, order skipped.");
         return false;
        }

      bool sent = direction > 0
                  ? g_levTrade.Buy(lots, _Symbol, price, sl, tp, comment)
                  : g_levTrade.Sell(lots, _Symbol, price, sl, tp, comment);
      uint retcode = g_levTrade.ResultRetcode();

      if(sent && (retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_DONE_PARTIAL ||
                  retcode == TRADE_RETCODE_PLACED))
         return true;
      if(retcode == TRADE_RETCODE_REQUOTE || retcode == TRADE_RETCODE_PRICE_CHANGED)
         continue;

      Print("Leviathan: order failed, retcode ", retcode);
      return false;
     }
   Print("Leviathan: order abandoned after repeated requotes.");
   return false;
  }

bool LevModifyStopLoss(const ulong ticket, const double newSL)
  {
   if(!PositionSelectByTicket(ticket))
      return false;
   double currentSL = PositionGetDouble(POSITION_SL);
   double tp        = PositionGetDouble(POSITION_TP);

   if(!LevFreezeAllows(currentSL) || !LevFreezeAllows(newSL))
      return false;
   if(g_levTrade.PositionModify(ticket, newSL, tp))
      return true;
   // NO_CHANGES means the level is already there; not an error worth logging
   return g_levTrade.ResultRetcode() == TRADE_RETCODE_NO_CHANGES;
  }

void LevApplyBreakEven(const double triggerR, const int offsetPoints, const double riskReward)
  {
   if(riskReward <= 0)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !LevIsOwnPosition())
         continue;

      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl    = PositionGetDouble(POSITION_SL);
      double tp    = PositionGetDouble(POSITION_TP);
      if(tp <= 0)
         continue;
      // Initial risk distance recovered from the unchanged TP and configured R:R
      double riskDistance = MathAbs(tp - entry) / riskReward;
      if(riskDistance <= 0)
         continue;

      long type = PositionGetInteger(POSITION_TYPE);
      double offset = offsetPoints * LevPoint();
      double minDist = LevMinStopDistance();

      if(type == POSITION_TYPE_BUY && sl < entry && tick.bid - entry >= riskDistance * triggerR)
        {
         double newSL = LevNormalizePrice(entry + offset);
         if(tick.bid - newSL >= minDist)
            LevModifyStopLoss(ticket, newSL);
        }
      if(type == POSITION_TYPE_SELL && (sl > entry || sl == 0) && entry - tick.ask >= riskDistance * triggerR)
        {
         double newSL = LevNormalizePrice(entry - offset);
         if(newSL - tick.ask >= minDist)
            LevModifyStopLoss(ticket, newSL);
        }
     }
  }

void LevApplyTrailing(const double atrMultiplier)
  {
   double atr = LevAtrValue(1);
   if(atr == EMPTY_VALUE || atr <= 0)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;
   double trailDistance = atr * atrMultiplier;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !LevIsOwnPosition())
         continue;

      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl    = PositionGetDouble(POSITION_SL);
      long   type  = PositionGetInteger(POSITION_TYPE);

      if(type == POSITION_TYPE_BUY)
        {
         double newSL = LevNormalizePrice(tick.bid - trailDistance);
         // Trail only in profit and never loosen the stop
         if(newSL > sl && newSL >= entry && (tick.bid - newSL) >= LevMinStopDistance())
            LevModifyStopLoss(ticket, newSL);
        }
      else
        {
         double newSL = LevNormalizePrice(tick.ask + trailDistance);
         if((newSL < sl || sl == 0) && newSL <= entry && (newSL - tick.ask) >= LevMinStopDistance())
            LevModifyStopLoss(ticket, newSL);
        }
     }
  }

void LevCloseAllPositions()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !LevIsOwnPosition())
         continue;
      if(!g_levTrade.PositionClose(ticket))
         Print("Leviathan: failed to close position ", ticket, ", retcode ", g_levTrade.ResultRetcode());
     }
  }

#endif
