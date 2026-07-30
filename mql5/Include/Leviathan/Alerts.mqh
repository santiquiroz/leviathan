//+------------------------------------------------------------------+
//| Leviathan - Alerts.mqh                                           |
//| Notifications and on-chart signal drawings                       |
//+------------------------------------------------------------------+
#ifndef LEVIATHAN_ALERTS_MQH
#define LEVIATHAN_ALERTS_MQH

#define LEV_DRAW_PFX "LEV_DRAW_"

void LevSendAlerts(const bool popup, const bool push, const bool email, const string message)
  {
   if(popup)
      Alert(message);
   if(push)
      SendNotification(message);
   if(email)
      SendMail("Leviathan - New Signal", message);
  }

void LevDrawLevelLine(const string name, const double price, const color lineColor, const string text)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, 0);
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, lineColor);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

void LevDrawSignal(const int direction, const double entry, const double sl, const double tp)
  {
   string arrowName = LEV_DRAW_PFX + "arrow";
   datetime barTime = iTime(_Symbol, _Period, 1);

   if(ObjectFind(0, arrowName) < 0)
      ObjectCreate(0, arrowName, OBJ_ARROW, 0, 0, 0);
   ObjectSetInteger(0, arrowName, OBJPROP_TIME, barTime);
   ObjectSetDouble(0, arrowName, OBJPROP_PRICE, entry);
   ObjectSetInteger(0, arrowName, OBJPROP_ARROWCODE, direction > 0 ? 233 : 234);
   ObjectSetInteger(0, arrowName, OBJPROP_COLOR, direction > 0 ? clrLimeGreen : clrTomato);
   ObjectSetInteger(0, arrowName, OBJPROP_WIDTH, 3);
   ObjectSetInteger(0, arrowName, OBJPROP_SELECTABLE, false);

   LevDrawLevelLine(LEV_DRAW_PFX + "entry", entry, clrDodgerBlue, "Leviathan Entry " + DoubleToString(entry, _Digits));
   LevDrawLevelLine(LEV_DRAW_PFX + "sl",    sl,    clrTomato,     "Leviathan SL "    + DoubleToString(sl, _Digits));
   LevDrawLevelLine(LEV_DRAW_PFX + "tp",    tp,    clrLimeGreen,  "Leviathan TP "    + DoubleToString(tp, _Digits));

   ChartRedraw();
  }

void LevClearDrawings()
  {
   ObjectDelete(0, LEV_DRAW_PFX + "arrow");
   ObjectDelete(0, LEV_DRAW_PFX + "entry");
   ObjectDelete(0, LEV_DRAW_PFX + "sl");
   ObjectDelete(0, LEV_DRAW_PFX + "tp");
  }

#endif
