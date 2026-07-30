//+------------------------------------------------------------------+
//| Leviathan - Broker.mqh                                           |
//| Broker normalization and validation helpers                      |
//+------------------------------------------------------------------+
#ifndef LEVIATHAN_BROKER_MQH
#define LEVIATHAN_BROKER_MQH

double LevPoint()
  {
   return SymbolInfoDouble(_Symbol, SYMBOL_POINT);
  }

double LevSpread()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return 0.0;
   return tick.ask - tick.bid;
  }

double LevNormalizePrice(double price)
  {
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize > 0)
      price = MathRound(price / tickSize) * tickSize;
   return NormalizeDouble(price, _Digits);
  }

double LevNormalizeLots(double lots)
  {
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0)
      lots = MathFloor(lots / step) * step;
   return MathMin(MathMax(lots, minLot), maxLot);
  }

double LevMinStopDistance()
  {
   long stopsLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double dist = stopsLevel * LevPoint();
   // Floating stop levels read 0 on many ECN brokers; use 3x spread as the floor
   if(dist <= 0)
      dist = 3.0 * LevSpread();
   return dist;
  }

bool LevStopsValid(const int direction, const double entry, const double sl, const double tp)
  {
   double minDist = LevMinStopDistance();
   if(direction > 0)
      return (entry - sl) >= minDist && (tp - entry) >= minDist;
   return (sl - entry) >= minDist && (entry - tp) >= minDist;
  }

double LevMoneyPerPoint(const double lots)
  {
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0)
      return 0.0;
   return lots * tickValue * (LevPoint() / tickSize);
  }

bool LevFreezeAllows(const double level)
  {
   long freeze = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   if(freeze <= 0)
      return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return false;
   double dist = freeze * LevPoint();
   return MathAbs(tick.bid - level) >= dist && MathAbs(tick.ask - level) >= dist;
  }

#endif
