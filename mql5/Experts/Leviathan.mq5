//+------------------------------------------------------------------+
//| Leviathan.mq5                                                    |
//| Open-source trend-filtered price action Expert Advisor           |
//| https://github.com/santiquiroz/leviathan - MIT License           |
//+------------------------------------------------------------------+
#property copyright "Leviathan contributors - MIT License"
#property link      "https://github.com/santiquiroz/leviathan"
#property version   "1.00"
#property description "Trend-filtered price action: EMA filter + Break of Structure + Engulfing/Pinbar."
#property description "Signals-only by default. Enable auto-trading explicitly. Educational software - use at your own risk."
#property strict

#include <Leviathan/Broker.mqh>
#include <Leviathan/Signals.mqh>
#include <Leviathan/Risk.mqh>
#include <Leviathan/TradeManager.mqh>
#include <Leviathan/Filters.mqh>
#include <Leviathan/Alerts.mqh>
#include <Leviathan/Panel.mqh>

enum ENUM_LEV_EXECUTION
  {
   LEV_SIGNALS_ONLY = 0, // Signals only (alerts, no orders) - recommended
   LEV_AUTO_TRADE   = 1  // Auto-trading (EA sends orders)
  };

input group "=== STRATEGY ==="
input int             InpEmaFast            = 9;       // Fast EMA period
input int             InpEmaSlow            = 21;      // Slow EMA period
input int             InpEmaTrend           = 200;     // Macro trend EMA period
input ENUM_MA_METHOD  InpMaMethod           = MODE_EMA; // Moving average method
input int             InpStructureLookback  = 20;      // Bars for Break of Structure
input bool            InpUseEngulfing       = true;    // Engulfing entry trigger
input bool            InpUsePinbar          = true;    // Pinbar entry trigger
input double          InpPinbarWickRatio    = 0.66;    // Min dominant wick fraction of range

input group "=== RISK ==="
input double          InpRiskReward         = 2.0;     // Risk:Reward ratio
input ENUM_LEV_SL_MODE InpSlMode            = LEV_SL_ATR; // Stop loss mode
input int             InpAtrPeriod          = 14;      // ATR period
input double          InpAtrMultiplier      = 1.5;     // ATR multiplier for SL
input int             InpSwingLookback      = 10;      // Bars for swing SL
input ENUM_LEV_SIZING InpSizingMode         = LEV_SIZE_FIXED_LOT; // Position sizing mode
input double          InpLotSize            = 0.10;    // Fixed lot size
input double          InpRiskPercent        = 1.0;     // Risk % of equity per trade

input group "=== TRADE MANAGEMENT ==="
input bool            InpUseBreakEven       = false;   // Move SL to break-even
input double          InpBreakEvenTriggerR  = 1.0;     // Break-even trigger (R multiple)
input int             InpBreakEvenOffsetPts = 0;       // Break-even offset (points)
input bool            InpUseTrailing        = false;   // ATR trailing stop
input double          InpTrailingAtrMult    = 2.0;     // Trailing distance (ATR multiple)

input group "=== FILTERS ==="
input bool            InpUseSessionFilter   = false;   // Trade only inside session window
input int             InpSessionStartHour   = 7;       // Session start hour (server time)
input int             InpSessionEndHour     = 20;      // Session end hour (server time)
input bool            InpUseSpreadFilter    = false;   // Skip signals on wide spread
input int             InpMaxSpreadPoints    = 30;      // Max spread (points)
input bool            InpUseDailyLossLimit  = false;   // Daily loss limit (auto mode)
input double          InpDailyLossPercent   = 3.0;     // Max daily equity loss %

input group "=== EXECUTION ==="
input ENUM_LEV_EXECUTION InpExecutionMode   = LEV_SIGNALS_ONLY; // Operating mode
input bool            InpOnePositionOnly    = true;    // Single concurrent position

input group "=== ALERTS ==="
input bool            InpAlertPopup         = true;    // Terminal popup alert
input bool            InpAlertPush          = true;    // Push notification
input bool            InpAlertEmail         = false;   // Email notification
input string          InpAlertWebhookUrl    = "";      // Webhook URL (Discord/Slack; whitelist in MT5 options)
input bool            InpLogSignals         = true;    // Log signals to file (MQL5/Files/Leviathan_signals.csv)

input group "=== GENERAL ==="
input long            InpMagicNumber        = 226701;      // Magic number
input string          InpTradeComment       = "Leviathan"; // Trade comment
input int             InpDeviationPoints    = 10;          // Max price deviation (points)
input bool            InpShowPanel          = true;        // Show chart panel

bool     g_active          = true;
datetime g_lastBarTime     = 0;
string   g_lastSignalText  = "None";
double   g_lastEntry       = 0.0;
double   g_lastSL          = 0.0;
double   g_lastTP          = 0.0;
int      g_currentDay      = 0;
double   g_dayStartEquity  = 0.0;
bool     g_dailyBlocked    = false;

bool ValidateInputs()
  {
   if(InpEmaFast <= 0 || InpEmaSlow <= 0 || InpEmaTrend <= 0 || InpAtrPeriod <= 0)
      return false;
   if(InpStructureLookback <= 0 || InpSwingLookback <= 0)
      return false;
   if(InpPinbarWickRatio <= 0 || InpPinbarWickRatio >= 1)
      return false;
   if(InpRiskReward <= 0 || InpLotSize <= 0 || InpRiskPercent <= 0)
      return false;
   return true;
  }

int OnInit()
  {
   if(!ValidateInputs())
     {
      Print("Leviathan: invalid input parameters.");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(!LevSignalsInit(InpEmaFast, InpEmaSlow, InpEmaTrend, InpMaMethod, InpAtrPeriod))
     {
      Print("Leviathan: failed to create indicator handles.");
      return INIT_FAILED;
     }
   LevTradeInit(InpMagicNumber, InpDeviationPoints);
   // Skip the partially-formed bar present at attach time; first evaluation
   // happens on the first tick of the next bar (spec: bar indexing convention)
   g_lastBarTime = iTime(_Symbol, _Period, 0);

   if(InpShowPanel)
     {
      LevPanelCreate(InpExecutionMode == LEV_AUTO_TRADE);
      EventSetTimer(1);
     }
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(InpShowPanel)
     {
      EventKillTimer();
      LevPanelDestroy();
     }
   LevClearDrawings();
   LevSignalsDeinit();
   ChartRedraw();
  }

bool IsNewBar()
  {
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == g_lastBarTime)
      return false;
   g_lastBarTime = currentBarTime;
   return true;
  }

void UpdateDailyState()
  {
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   int today = now.year * 10000 + now.mon * 100 + now.day;
   if(today == g_currentDay)
      return;
   g_currentDay     = today;
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_dailyBlocked   = false;
  }

void EnforceDailyLossLimit()
  {
   if(!InpUseDailyLossLimit || InpExecutionMode != LEV_AUTO_TRADE)
      return;
   UpdateDailyState();
   if(g_dailyBlocked || g_dayStartEquity <= 0)
      return;
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= g_dayStartEquity * (1.0 - InpDailyLossPercent / 100.0))
     {
      LevCloseAllPositions();
      g_dailyBlocked = true;
      Print("Leviathan: daily loss limit hit (", InpDailyLossPercent, "%). Trading paused until next day.");
     }
  }

void RefreshPanel()
  {
   if(!InpShowPanel)
      return;
   LevPanelUpdate(g_active, InpExecutionMode == LEV_AUTO_TRADE, LevTrendLabel(LevTrendDirection()),
                  g_lastSignalText, InpRiskReward, g_lastEntry, g_lastSL, g_lastTP);
  }

void ProcessSignal(const int direction, const string patternName)
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   double entry = direction > 0 ? tick.ask : tick.bid;
   double sl = LevCalcStopLoss(direction, entry, InpSlMode, InpAtrMultiplier, InpSwingLookback);
   if(sl <= 0)
      return;
   double tp = LevCalcTakeProfit(direction, entry, sl, InpRiskReward);
   if(tp <= 0)
      return;

   double lots = LevCalcLots(InpSizingMode, InpLotSize, InpRiskPercent, entry, sl);

   g_lastEntry      = entry;
   g_lastSL         = sl;
   g_lastTP         = tp;
   g_lastSignalText = (direction > 0 ? "LONG - " : "SHORT - ") + patternName;

   LevDrawSignal(direction, entry, sl, tp);

   string message = StringFormat("Leviathan | %s %s | %s | Entry: %s | SL: %s | TP: %s | Lots: %.2f",
                                 _Symbol, EnumToString(_Period), g_lastSignalText,
                                 DoubleToString(entry, _Digits), DoubleToString(sl, _Digits),
                                 DoubleToString(tp, _Digits), lots);
   LevSendAlerts(InpAlertPopup, InpAlertPush, InpAlertEmail, message);
   LevSendWebhook(InpAlertWebhookUrl, message);
   if(InpLogSignals)
      LevLogSignal(direction, patternName, entry, sl, tp, lots);

   if(InpExecutionMode != LEV_AUTO_TRADE)
      return;
   if(g_dailyBlocked)
      return;
   if(InpOnePositionOnly && LevHasOpenPosition())
      return;
   if(lots <= 0)
      return;
   LevOpenPosition(direction, lots, sl, tp, InpTradeComment);
  }

void CheckForSignal()
  {
   string patternName = "";
   int direction = LevDetectSignal(InpStructureLookback, InpUseEngulfing, InpUsePinbar,
                                   InpPinbarWickRatio, patternName);
   if(direction != LEV_DIR_NONE &&
      LevSessionAllows(InpUseSessionFilter, InpSessionStartHour, InpSessionEndHour) &&
      LevSpreadAllows(InpUseSpreadFilter, InpMaxSpreadPoints))
      ProcessSignal(direction, patternName);

   RefreshPanel();
  }

void OnTick()
  {
   if(InpExecutionMode == LEV_AUTO_TRADE)
     {
      if(InpUseBreakEven)
         LevApplyBreakEven(InpBreakEvenTriggerR, InpBreakEvenOffsetPts, InpRiskReward);
      if(InpUseTrailing)
         LevApplyTrailing(InpTrailingAtrMult);
      EnforceDailyLossLimit();
     }

   if(!g_active)
      return;
   if(!IsNewBar())
      return;
   CheckForSignal();
  }

void OnTimer()
  {
   RefreshPanel();
  }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(LevPanelToggleClicked(id, sparam))
     {
      g_active = !g_active;
      RefreshPanel();
      Print("Leviathan: signals ", g_active ? "resumed" : "paused", " by user.");
     }
  }
//+------------------------------------------------------------------+
