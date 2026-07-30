//+------------------------------------------------------------------+
//| Leviathan - Signals.mqh                                          |
//| Trend filter, break of structure and candle pattern detection    |
//| All logic reads closed bars only (shift >= 1). See docs/STRATEGY.md |
//+------------------------------------------------------------------+
#ifndef LEVIATHAN_SIGNALS_MQH
#define LEVIATHAN_SIGNALS_MQH

#define LEV_DIR_NONE   0
#define LEV_DIR_LONG   1
#define LEV_DIR_SHORT -1

int g_levEmaFastHandle  = INVALID_HANDLE;
int g_levEmaSlowHandle  = INVALID_HANDLE;
int g_levEmaTrendHandle = INVALID_HANDLE;
int g_levAtrHandle      = INVALID_HANDLE;

bool LevSignalsInit(const int emaFast, const int emaSlow, const int emaTrend,
                    const ENUM_MA_METHOD maMethod, const int atrPeriod)
  {
   g_levEmaFastHandle  = iMA(_Symbol, _Period, emaFast,  0, maMethod, PRICE_CLOSE);
   g_levEmaSlowHandle  = iMA(_Symbol, _Period, emaSlow,  0, maMethod, PRICE_CLOSE);
   g_levEmaTrendHandle = iMA(_Symbol, _Period, emaTrend, 0, maMethod, PRICE_CLOSE);
   g_levAtrHandle      = iATR(_Symbol, _Period, atrPeriod);

   return g_levEmaFastHandle  != INVALID_HANDLE &&
          g_levEmaSlowHandle  != INVALID_HANDLE &&
          g_levEmaTrendHandle != INVALID_HANDLE &&
          g_levAtrHandle      != INVALID_HANDLE;
  }

void LevSignalsDeinit()
  {
   if(g_levEmaFastHandle  != INVALID_HANDLE) IndicatorRelease(g_levEmaFastHandle);
   if(g_levEmaSlowHandle  != INVALID_HANDLE) IndicatorRelease(g_levEmaSlowHandle);
   if(g_levEmaTrendHandle != INVALID_HANDLE) IndicatorRelease(g_levEmaTrendHandle);
   if(g_levAtrHandle      != INVALID_HANDLE) IndicatorRelease(g_levAtrHandle);
   g_levEmaFastHandle  = INVALID_HANDLE;
   g_levEmaSlowHandle  = INVALID_HANDLE;
   g_levEmaTrendHandle = INVALID_HANDLE;
   g_levAtrHandle      = INVALID_HANDLE;
  }

double LevBufferValue(const int handle, const int shift)
  {
   if(handle == INVALID_HANDLE || BarsCalculated(handle) <= shift)
      return EMPTY_VALUE;
   double buffer[1];
   ArraySetAsSeries(buffer, true);
   if(CopyBuffer(handle, 0, shift, 1, buffer) != 1)
      return EMPTY_VALUE;
   return buffer[0];
  }

double LevAtrValue(const int shift)
  {
   return LevBufferValue(g_levAtrHandle, shift);
  }

int LevTrendDirection()
  {
   double emaFast  = LevBufferValue(g_levEmaFastHandle, 1);
   double emaSlow  = LevBufferValue(g_levEmaSlowHandle, 1);
   double emaTrend = LevBufferValue(g_levEmaTrendHandle, 1);
   if(emaFast == EMPTY_VALUE || emaSlow == EMPTY_VALUE || emaTrend == EMPTY_VALUE)
      return LEV_DIR_NONE;

   double close1 = iClose(_Symbol, _Period, 1);
   if(emaFast > emaSlow && close1 > emaTrend)
      return LEV_DIR_LONG;
   if(emaFast < emaSlow && close1 < emaTrend)
      return LEV_DIR_SHORT;
   return LEV_DIR_NONE;
  }

string LevTrendLabel(const int trend)
  {
   if(trend == LEV_DIR_LONG)  return "BULLISH";
   if(trend == LEV_DIR_SHORT) return "BEARISH";
   return "NEUTRAL";
  }

double LevSwingHigh(const int lookback, const int startShift)
  {
   int index = iHighest(_Symbol, _Period, MODE_HIGH, lookback, startShift);
   if(index < 0)
      return 0.0;
   return iHigh(_Symbol, _Period, index);
  }

double LevSwingLow(const int lookback, const int startShift)
  {
   int index = iLowest(_Symbol, _Period, MODE_LOW, lookback, startShift);
   if(index < 0)
      return 0.0;
   return iLow(_Symbol, _Period, index);
  }

bool LevBrokeStructureUp(const int lookback)
  {
   double swingHigh = LevSwingHigh(lookback, 2);
   return swingHigh > 0 && iClose(_Symbol, _Period, 1) > swingHigh;
  }

bool LevBrokeStructureDown(const int lookback)
  {
   double swingLow = LevSwingLow(lookback, 2);
   return swingLow > 0 && iClose(_Symbol, _Period, 1) < swingLow;
  }

bool LevBullishEngulfing()
  {
   double open1  = iOpen(_Symbol, _Period, 1);
   double close1 = iClose(_Symbol, _Period, 1);
   double open2  = iOpen(_Symbol, _Period, 2);
   double close2 = iClose(_Symbol, _Period, 2);

   bool previousBearish = close2 < open2;
   bool currentBullish  = close1 > open1;
   bool bodyEngulfs     = close1 >= open2 && open1 <= close2;
   return previousBearish && currentBullish && bodyEngulfs;
  }

bool LevBearishEngulfing()
  {
   double open1  = iOpen(_Symbol, _Period, 1);
   double close1 = iClose(_Symbol, _Period, 1);
   double open2  = iOpen(_Symbol, _Period, 2);
   double close2 = iClose(_Symbol, _Period, 2);

   bool previousBullish = close2 > open2;
   bool currentBearish  = close1 < open1;
   bool bodyEngulfs     = open1 >= close2 && close1 <= open2;
   return previousBullish && currentBearish && bodyEngulfs;
  }

bool LevBullishPinbar(const double wickRatio)
  {
   double open1  = iOpen(_Symbol, _Period, 1);
   double close1 = iClose(_Symbol, _Period, 1);
   double high1  = iHigh(_Symbol, _Period, 1);
   double low1   = iLow(_Symbol, _Period, 1);

   double range = high1 - low1;
   if(range <= 0)
      return false;

   double lowerWick = MathMin(open1, close1) - low1;
   double upperWick = high1 - MathMax(open1, close1);
   return lowerWick / range >= wickRatio &&
          upperWick / range <= (1.0 - wickRatio) * 0.5;
  }

bool LevBearishPinbar(const double wickRatio)
  {
   double open1  = iOpen(_Symbol, _Period, 1);
   double close1 = iClose(_Symbol, _Period, 1);
   double high1  = iHigh(_Symbol, _Period, 1);
   double low1   = iLow(_Symbol, _Period, 1);

   double range = high1 - low1;
   if(range <= 0)
      return false;

   double upperWick = high1 - MathMax(open1, close1);
   double lowerWick = MathMin(open1, close1) - low1;
   return upperWick / range >= wickRatio &&
          lowerWick / range <= (1.0 - wickRatio) * 0.5;
  }

int LevDetectSignal(const int structureLookback, const bool useEngulfing,
                    const bool usePinbar, const double wickRatio, string &patternName)
  {
   int trend = LevTrendDirection();

   if(trend == LEV_DIR_LONG && LevBrokeStructureUp(structureLookback))
     {
      if(useEngulfing && LevBullishEngulfing())
        { patternName = "Bullish Engulfing"; return LEV_DIR_LONG; }
      if(usePinbar && LevBullishPinbar(wickRatio))
        { patternName = "Bullish Pinbar"; return LEV_DIR_LONG; }
     }

   if(trend == LEV_DIR_SHORT && LevBrokeStructureDown(structureLookback))
     {
      if(useEngulfing && LevBearishEngulfing())
        { patternName = "Bearish Engulfing"; return LEV_DIR_SHORT; }
      if(usePinbar && LevBearishPinbar(wickRatio))
        { patternName = "Bearish Pinbar"; return LEV_DIR_SHORT; }
     }

   patternName = "";
   return LEV_DIR_NONE;
  }

#endif
