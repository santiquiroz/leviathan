//+------------------------------------------------------------------+
//| Leviathan - Panel.mqh                                            |
//| On-chart status panel with pause/resume toggle                   |
//+------------------------------------------------------------------+
#ifndef LEVIATHAN_PANEL_MQH
#define LEVIATHAN_PANEL_MQH

#define LEV_PANEL_PFX "LEV_PANEL_"

int LEV_PANEL_X = 20;
int LEV_PANEL_Y = 30;
int LEV_PANEL_W = 300;
int LEV_PANEL_H = 330;

color LevPanelBackground = (color)0x1E1E1E;
color LevPanelBorder     = clrDimGray;
color LevPanelLabel      = clrLightGray;
color LevPanelValue      = clrWhite;
color LevPanelActiveBG   = clrSeaGreen;
color LevPanelInactiveBG = (color)0x2E2E2E;

void LevPanel_RectLabel(const string name, const int x, const int y, const int w, const int h,
                        const color bg, const color border)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, name, OBJPROP_COLOR, border);
   ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

void LevPanel_Label(const string name, const int x, const int y, const string text,
                    const int fontSize, const color textColor, const string font = "Segoe UI")
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_FONT, font);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fontSize);
   ObjectSetInteger(0, name, OBJPROP_COLOR, textColor);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

void LevPanel_Button(const string name, const int x, const int y, const int w, const int h,
                     const string text, const color bg, const color textColor)
  {
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_FONT, "Segoe UI");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 10);
   ObjectSetInteger(0, name, OBJPROP_COLOR, textColor);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, name, OBJPROP_BORDER_COLOR, LevPanelBorder);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_STATE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
  }

void LevPanel_Row(const string suffix, const int rowY, const string labelText)
  {
   LevPanel_Label(LEV_PANEL_PFX + "lbl_" + suffix, LEV_PANEL_X + 15, rowY, labelText, 9, LevPanelLabel);
   LevPanel_Label(LEV_PANEL_PFX + "val_" + suffix, LEV_PANEL_X + 170, rowY, "--", 9, LevPanelValue, "Segoe UI Bold");
  }

void LevPanel_SetValue(const string suffix, const string text, const color textColor)
  {
   string name = LEV_PANEL_PFX + "val_" + suffix;
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, textColor);
  }

string LevPanel_Price(const double value)
  {
   return value > 0 ? DoubleToString(value, _Digits) : "--";
  }

void LevPanelCreate(const bool autoTrading)
  {
   LevPanel_RectLabel(LEV_PANEL_PFX + "bg", LEV_PANEL_X, LEV_PANEL_Y, LEV_PANEL_W, LEV_PANEL_H,
                      LevPanelBackground, LevPanelBorder);
   LevPanel_Label(LEV_PANEL_PFX + "title", LEV_PANEL_X + 15, LEV_PANEL_Y + 12, "LEVIATHAN", 14, clrWhite, "Trebuchet MS");
   LevPanel_Label(LEV_PANEL_PFX + "link", LEV_PANEL_X + 15, LEV_PANEL_Y + 36,
                  "github.com/santiquiroz/leviathan", 8, clrSilver);
   LevPanel_RectLabel(LEV_PANEL_PFX + "sep", LEV_PANEL_X + 15, LEV_PANEL_Y + 58, LEV_PANEL_W - 30, 1,
                      LevPanelBorder, LevPanelBorder);

   LevPanel_Row("mode",   LEV_PANEL_Y + 70,  "Mode:");
   LevPanel_Row("status", LEV_PANEL_Y + 94,  "Status:");
   LevPanel_Row("trend",  LEV_PANEL_Y + 118, "Trend:");
   LevPanel_Row("signal", LEV_PANEL_Y + 142, "Last signal:");
   LevPanel_Row("rr",     LEV_PANEL_Y + 166, "R:R:");
   LevPanel_Row("entry",  LEV_PANEL_Y + 190, "Entry:");
   LevPanel_Row("sl",     LEV_PANEL_Y + 214, "SL:");
   LevPanel_Row("tp",     LEV_PANEL_Y + 238, "TP:");

   LevPanel_Button(LEV_PANEL_PFX + "toggle", LEV_PANEL_X + 15, LEV_PANEL_Y + 280, LEV_PANEL_W - 30, 40,
                   "SIGNALS ACTIVE - click to pause", LevPanelActiveBG, clrWhite);

   LevPanelUpdate(true, autoTrading, "NEUTRAL", "None", 0.0, 0.0, 0.0, 0.0);
   ChartRedraw();
  }

void LevPanelUpdate(const bool eaActive, const bool autoTrading, const string trendText,
                    const string signalText, const double riskReward,
                    const double entry, const double sl, const double tp)
  {
   if(ObjectFind(0, LEV_PANEL_PFX + "val_status") < 0)
      return;

   LevPanel_SetValue("mode", autoTrading ? "AUTO-TRADING" : "SIGNALS ONLY",
                     autoTrading ? clrOrange : clrDodgerBlue);
   LevPanel_SetValue("status", eaActive ? "ACTIVE" : "PAUSED",
                     eaActive ? clrLimeGreen : clrOrangeRed);

   color trendColor = LevPanelValue;
   if(trendText == "BULLISH") trendColor = clrLimeGreen;
   if(trendText == "BEARISH") trendColor = clrTomato;
   LevPanel_SetValue("trend", trendText, trendColor);

   LevPanel_SetValue("signal", signalText, LevPanelValue);
   LevPanel_SetValue("rr", riskReward > 0 ? StringFormat("1:%.1f", riskReward) : "--", LevPanelValue);
   LevPanel_SetValue("entry", LevPanel_Price(entry), clrDodgerBlue);
   LevPanel_SetValue("sl",    LevPanel_Price(sl),    clrTomato);
   LevPanel_SetValue("tp",    LevPanel_Price(tp),    clrLimeGreen);

   string toggleName = LEV_PANEL_PFX + "toggle";
   ObjectSetString(0, toggleName, OBJPROP_TEXT,
                   eaActive ? "SIGNALS ACTIVE - click to pause" : "SIGNALS PAUSED - click to activate");
   ObjectSetInteger(0, toggleName, OBJPROP_BGCOLOR, eaActive ? LevPanelActiveBG : LevPanelInactiveBG);
   ObjectSetInteger(0, toggleName, OBJPROP_COLOR, eaActive ? clrWhite : clrLightGray);

   ChartRedraw();
  }

bool LevPanelToggleClicked(const int id, const string &sparam)
  {
   if(id != CHARTEVENT_OBJECT_CLICK || sparam != LEV_PANEL_PFX + "toggle")
      return false;
   ObjectSetInteger(0, LEV_PANEL_PFX + "toggle", OBJPROP_STATE, false);
   return true;
  }

void LevPanelDestroy()
  {
   ObjectDelete(0, LEV_PANEL_PFX + "bg");
   ObjectDelete(0, LEV_PANEL_PFX + "title");
   ObjectDelete(0, LEV_PANEL_PFX + "link");
   ObjectDelete(0, LEV_PANEL_PFX + "sep");
   string rows[8] = {"mode", "status", "trend", "signal", "rr", "entry", "sl", "tp"};
   for(int i = 0; i < 8; i++)
     {
      ObjectDelete(0, LEV_PANEL_PFX + "lbl_" + rows[i]);
      ObjectDelete(0, LEV_PANEL_PFX + "val_" + rows[i]);
     }
   ObjectDelete(0, LEV_PANEL_PFX + "toggle");
   ChartRedraw();
  }

#endif
