//+------------------------------------------------------------------+
//| Leviathan - Risk.mqh                                             |
//| Stop loss, take profit and position sizing calculations          |
//+------------------------------------------------------------------+
#ifndef LEVIATHAN_RISK_MQH
#define LEVIATHAN_RISK_MQH

#include "Broker.mqh"
#include "Signals.mqh"

enum ENUM_LEV_SL_MODE
  {
   LEV_SL_ATR   = 0, // ATR-based stop loss
   LEV_SL_SWING = 1  // Structure (swing) stop loss
  };

enum ENUM_LEV_SIZING
  {
   LEV_SIZE_FIXED_LOT    = 0, // Fixed lot size
   LEV_SIZE_RISK_PERCENT = 1  // Risk % of equity per trade
  };

double LevCalcStopLoss(const int direction, const double entry, const ENUM_LEV_SL_MODE mode,
                       const double atrMultiplier, const int swingLookback)
  {
   double sl = 0.0;

   if(mode == LEV_SL_ATR)
     {
      double atr = LevAtrValue(1);
      if(atr == EMPTY_VALUE || atr <= 0)
         return 0.0;
      sl = direction > 0 ? entry - atr * atrMultiplier : entry + atr * atrMultiplier;
     }
   else
     {
      sl = direction > 0 ? LevSwingLow(swingLookback, 2) : LevSwingHigh(swingLookback, 2);
     }

   if(sl <= 0)
      return 0.0;
   if(direction > 0 && sl >= entry)
      return 0.0;
   if(direction < 0 && sl <= entry)
      return 0.0;
   return LevNormalizePrice(sl);
  }

double LevCalcTakeProfit(const int direction, const double entry, const double sl, const double riskReward)
  {
   double distance = MathAbs(entry - sl);
   if(distance <= 0)
      return 0.0;
   double tp = direction > 0 ? entry + distance * riskReward : entry - distance * riskReward;
   return LevNormalizePrice(tp);
  }

double LevCalcLots(const ENUM_LEV_SIZING sizingMode, const double fixedLot,
                   const double riskPercent, const double entry, const double sl)
  {
   if(sizingMode == LEV_SIZE_FIXED_LOT)
      return LevNormalizeLots(fixedLot);

   double point = LevPoint();
   double perPointOneLot = LevMoneyPerPoint(1.0);
   if(point <= 0 || perPointOneLot <= 0)
      return 0.0;

   double stopPoints = MathAbs(entry - sl) / point;
   if(stopPoints <= 0)
      return 0.0;

   double riskMoney = AccountInfoDouble(ACCOUNT_EQUITY) * riskPercent / 100.0;
   return LevNormalizeLots(riskMoney / (stopPoints * perPointOneLot));
  }

#endif
