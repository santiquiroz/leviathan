//+------------------------------------------------------------------+
//| Leviathan - Filters.mqh                                          |
//| Optional entry filters: session window, max spread               |
//+------------------------------------------------------------------+
#ifndef LEVIATHAN_FILTERS_MQH
#define LEVIATHAN_FILTERS_MQH

#include "Broker.mqh"

bool LevSessionAllows(const bool enabled, const int startHour, const int endHour)
  {
   if(!enabled)
      return true;
   // start == end means no restriction (same semantics as the Python engine)
   if(startHour == endHour)
      return true;
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   if(startHour < endHour)
      return now.hour >= startHour && now.hour < endHour;
   // Window crosses midnight (e.g. 22 -> 6)
   return now.hour >= startHour || now.hour < endHour;
  }

bool LevSpreadAllows(const bool enabled, const int maxSpreadPoints)
  {
   if(!enabled)
      return true;
   double point = LevPoint();
   if(point <= 0)
      return false;
   return LevSpread() / point <= maxSpreadPoints;
  }

#endif
