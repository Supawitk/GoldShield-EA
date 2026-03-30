//+------------------------------------------------------------------+
//| GoldShield_EA.mq5                                                |
//| Safety-First XAUUSD Expert Advisor                               |
//| EMA Cross + RSI Filter + ATR Dynamic Risk Management             |
//+------------------------------------------------------------------+
#property copyright "GoldShield EA"
#property version   "1.00"
#property description "Safety-first XAUUSD EA: EMA crossover entries, RSI filter, ATR-based SL/TP/trailing stop"
#property strict

#include <Trade/Trade.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+

//--- General Settings
input ulong  MagicNumber    = 20260330;     // Magic Number
input string TradeComment   = "GoldShield"; // Trade Comment

//--- Indicator Settings
input int    EMA_Fast_Period = 50;          // Fast EMA Period
input int    EMA_Slow_Period = 200;         // Slow EMA Period
input int    RSI_Period      = 14;          // RSI Period
input double RSI_Overbought  = 70.0;       // RSI Overbought Level
input double RSI_Oversold    = 30.0;       // RSI Oversold Level
input int    ATR_Period      = 14;          // ATR Period

//--- Risk Management
input double RiskPercent          = 1.0;    // Risk Per Trade (%)
input double SL_ATR_Multiplier    = 1.5;    // Stop Loss ATR Multiplier
input double TP_ATR_Multiplier    = 1.0;    // Take Profit ATR Multiplier
input double TrailingStop_ATR_Mult = 1.0;   // Trailing Stop ATR Multiplier
input int    TrailingStep_Points   = 50;    // Trailing Stop Min Step (points)

//--- Safety Filters
input int    MaxSpreadPoints       = 50;    // Max Spread (points)
input int    MaxOpenPositions      = 1;     // Max Open Positions
input double DailyLossLimitPercent = 3.0;   // Daily Loss Limit (%)
input int    MinBarsBetweenTrades  = 5;     // Min Bars Between Trades
input int    TradingStartHour      = 2;     // Trading Start Hour (server time)
input int    TradingEndHour        = 21;    // Trading End Hour (server time)

//+------------------------------------------------------------------+
//| Enums                                                             |
//+------------------------------------------------------------------+
enum ENUM_SIGNAL
{
   SIGNAL_NONE = 0,
   SIGNAL_BUY  = 1,
   SIGNAL_SELL = 2
};

//+------------------------------------------------------------------+
//| Global Variables                                                   |
//+------------------------------------------------------------------+
int    handleEMA_Fast;
int    handleEMA_Slow;
int    handleRSI;
int    handleATR;

CTrade trade;

datetime lastTradeBarTime;
double   dailyStartBalance;
int      currentDay;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Validate inputs
   if(EMA_Fast_Period >= EMA_Slow_Period)
   {
      Print("ERROR: EMA_Fast_Period (", EMA_Fast_Period, ") must be less than EMA_Slow_Period (", EMA_Slow_Period, ")");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(RiskPercent < 0.1 || RiskPercent > 5.0)
   {
      Print("ERROR: RiskPercent must be between 0.1 and 5.0, got: ", RiskPercent);
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(RSI_Overbought <= RSI_Oversold)
   {
      Print("ERROR: RSI_Overbought must be greater than RSI_Oversold");
      return(INIT_PARAMETERS_INCORRECT);
   }

   //--- Create indicator handles
   handleEMA_Fast = iMA(_Symbol, PERIOD_H1, EMA_Fast_Period, 0, MODE_EMA, PRICE_CLOSE);
   if(handleEMA_Fast == INVALID_HANDLE)
   {
      Print("ERROR: Failed to create EMA Fast handle");
      return(INIT_FAILED);
   }

   handleEMA_Slow = iMA(_Symbol, PERIOD_H1, EMA_Slow_Period, 0, MODE_EMA, PRICE_CLOSE);
   if(handleEMA_Slow == INVALID_HANDLE)
   {
      Print("ERROR: Failed to create EMA Slow handle");
      return(INIT_FAILED);
   }

   handleRSI = iRSI(_Symbol, PERIOD_H1, RSI_Period, PRICE_CLOSE);
   if(handleRSI == INVALID_HANDLE)
   {
      Print("ERROR: Failed to create RSI handle");
      return(INIT_FAILED);
   }

   handleATR = iATR(_Symbol, PERIOD_H1, ATR_Period);
   if(handleATR == INVALID_HANDLE)
   {
      Print("ERROR: Failed to create ATR handle");
      return(INIT_FAILED);
   }

   //--- Configure CTrade
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(30);
   trade.SetTypeFilling(GetFillingMode());

   //--- Initialize daily tracking
   dailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   MqlDateTime dt;
   TimeCurrent(dt);
   currentDay = dt.day_of_year;

   //--- Restore state from existing positions (handles terminal restart)
   lastTradeBarTime = 0;
   RestoreStateFromPositions();

   //--- Log startup
   Print("=== GoldShield EA Initialized ===");
   Print("Symbol: ", _Symbol, " | Timeframe: H1");
   Print("EMA Fast: ", EMA_Fast_Period, " | EMA Slow: ", EMA_Slow_Period);
   Print("RSI: ", RSI_Period, " (OB:", RSI_Overbought, " OS:", RSI_Oversold, ")");
   Print("ATR: ", ATR_Period, " | SL mult: ", SL_ATR_Multiplier, " | TP mult: ", TP_ATR_Multiplier);
   Print("Risk: ", RiskPercent, "% | Max Spread: ", MaxSpreadPoints, " pts");
   Print("Trading Hours: ", TradingStartHour, ":00 - ", TradingEndHour, ":00");
   Print("Daily Loss Limit: ", DailyLossLimitPercent, "% | Cooldown: ", MinBarsBetweenTrades, " bars");

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(handleEMA_Fast != INVALID_HANDLE) IndicatorRelease(handleEMA_Fast);
   if(handleEMA_Slow != INVALID_HANDLE) IndicatorRelease(handleEMA_Slow);
   if(handleRSI      != INVALID_HANDLE) IndicatorRelease(handleRSI);
   if(handleATR      != INVALID_HANDLE) IndicatorRelease(handleATR);

   Print("GoldShield EA removed. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Step 1: Always manage trailing stop on every tick
   ManageTrailingStop();

   //--- Step 2: Only evaluate new signals on a new H1 bar
   if(!IsNewBar())
      return;

   //--- Step 3: Reset daily tracking if day changed
   ResetDailyTracking();

   //--- Step 4-8: Safety guards
   if(IsDailyLossLimitHit())   return;
   if(!IsTradingHoursAllowed()) return;
   if(IsMaxPositionsReached())  return;
   if(!IsSpreadAcceptable())    return;
   if(IsCooldownActive())       return;

   //--- Step 9: Copy indicator data
   double emaFast[], emaSlow[], rsi[], atr[];
   if(!CopyIndicatorData(emaFast, emaSlow, rsi, atr))
      return;

   //--- Step 10: Evaluate signal
   ENUM_SIGNAL signal = EvaluateSignal(emaFast, emaSlow, rsi);

   //--- Step 11: Execute trade
   if(signal == SIGNAL_BUY)
   {
      double slDist = atr[1] * SL_ATR_Multiplier;
      double tpDist = atr[1] * TP_ATR_Multiplier;
      ExecuteBuy(slDist, tpDist);
   }
   else if(signal == SIGNAL_SELL)
   {
      double slDist = atr[1] * SL_ATR_Multiplier;
      double tpDist = atr[1] * TP_ATR_Multiplier;
      ExecuteSell(slDist, tpDist);
   }
}

//+------------------------------------------------------------------+
//| Check for new H1 bar                                              |
//+------------------------------------------------------------------+
bool IsNewBar()
{
   static datetime lastBarTime = 0;
   datetime barTime = iTime(_Symbol, PERIOD_H1, 0);

   if(barTime == lastBarTime)
      return false;

   lastBarTime = barTime;
   return true;
}

//+------------------------------------------------------------------+
//| Copy all indicator buffers                                        |
//+------------------------------------------------------------------+
bool CopyIndicatorData(double &emaFast[], double &emaSlow[], double &rsi[], double &atr[])
{
   ArraySetAsSeries(emaFast, true);
   ArraySetAsSeries(emaSlow, true);
   ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(atr, true);

   if(CopyBuffer(handleEMA_Fast, 0, 0, 3, emaFast) < 3)
   {
      Print(__FUNCTION__, ": Failed to copy EMA Fast buffer");
      return false;
   }
   if(CopyBuffer(handleEMA_Slow, 0, 0, 3, emaSlow) < 3)
   {
      Print(__FUNCTION__, ": Failed to copy EMA Slow buffer");
      return false;
   }
   if(CopyBuffer(handleRSI, 0, 0, 2, rsi) < 2)
   {
      Print(__FUNCTION__, ": Failed to copy RSI buffer");
      return false;
   }
   if(CopyBuffer(handleATR, 0, 0, 2, atr) < 2)
   {
      Print(__FUNCTION__, ": Failed to copy ATR buffer");
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
//| Evaluate trading signal                                           |
//+------------------------------------------------------------------+
ENUM_SIGNAL EvaluateSignal(const double &emaFast[], const double &emaSlow[], const double &rsi[])
{
   //--- Use index [1] (last completed bar) and [2] (bar before) to avoid repainting
   double close = iClose(_Symbol, PERIOD_H1, 1);

   //--- BUY: EMA50 crosses above EMA200, price above EMA200, RSI not overbought
   if(emaFast[1] > emaSlow[1] && emaFast[2] <= emaSlow[2])
   {
      if(close > emaSlow[1])
      {
         if(rsi[1] < RSI_Overbought && rsi[1] > RSI_Oversold)
         {
            Print("BUY signal detected | EMA Fast: ", emaFast[1], " > EMA Slow: ", emaSlow[1],
                  " | RSI: ", rsi[1], " | Close: ", close);
            return SIGNAL_BUY;
         }
      }
   }

   //--- SELL: EMA50 crosses below EMA200, price below EMA200, RSI not oversold
   if(emaFast[1] < emaSlow[1] && emaFast[2] >= emaSlow[2])
   {
      if(close < emaSlow[1])
      {
         if(rsi[1] > RSI_Oversold && rsi[1] < RSI_Overbought)
         {
            Print("SELL signal detected | EMA Fast: ", emaFast[1], " < EMA Slow: ", emaSlow[1],
                  " | RSI: ", rsi[1], " | Close: ", close);
            return SIGNAL_SELL;
         }
      }
   }

   return SIGNAL_NONE;
}

//+------------------------------------------------------------------+
//| Execute BUY trade                                                 |
//+------------------------------------------------------------------+
void ExecuteBuy(double slDistance, double tpDistance)
{
   double lots = CalculateLotSize(slDistance);
   if(lots <= 0)
   {
      Print("WARNING: Lot size is 0, insufficient balance for this risk level");
      return;
   }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl  = NormalizeDouble(ask - slDistance, _Digits);
   double tp  = NormalizeDouble(ask + tpDistance, _Digits);

   //--- Check minimum stop distance
   sl = EnforceMinStopDistance(ask, sl, true);

   if(trade.Buy(lots, _Symbol, ask, sl, tp, TradeComment))
   {
      if(trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED)
      {
         lastTradeBarTime = iTime(_Symbol, PERIOD_H1, 0);
         Print("BUY executed | Lots: ", lots, " | Price: ", ask, " | SL: ", sl, " | TP: ", tp);
      }
      else
      {
         Print("BUY order issue | Code: ", trade.ResultRetcode(), " | ", trade.ResultComment());
      }
   }
   else
   {
      Print("BUY failed | Code: ", trade.ResultRetcode(), " | ", trade.ResultComment());
   }
}

//+------------------------------------------------------------------+
//| Execute SELL trade                                                |
//+------------------------------------------------------------------+
void ExecuteSell(double slDistance, double tpDistance)
{
   double lots = CalculateLotSize(slDistance);
   if(lots <= 0)
   {
      Print("WARNING: Lot size is 0, insufficient balance for this risk level");
      return;
   }

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl  = NormalizeDouble(bid + slDistance, _Digits);
   double tp  = NormalizeDouble(bid - tpDistance, _Digits);

   //--- Check minimum stop distance
   sl = EnforceMinStopDistance(bid, sl, false);

   if(trade.Sell(lots, _Symbol, bid, sl, tp, TradeComment))
   {
      if(trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED)
      {
         lastTradeBarTime = iTime(_Symbol, PERIOD_H1, 0);
         Print("SELL executed | Lots: ", lots, " | Price: ", bid, " | SL: ", sl, " | TP: ", tp);
      }
      else
      {
         Print("SELL order issue | Code: ", trade.ResultRetcode(), " | ", trade.ResultComment());
      }
   }
   else
   {
      Print("SELL failed | Code: ", trade.ResultRetcode(), " | ", trade.ResultComment());
   }
}

//+------------------------------------------------------------------+
//| Calculate lot size based on risk percentage                       |
//+------------------------------------------------------------------+
double CalculateLotSize(double slDistancePrice)
{
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double lotStep   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   if(tickSize == 0 || tickValue == 0 || lotStep == 0)
   {
      Print(__FUNCTION__, ": Invalid symbol info (tickSize/tickValue/lotStep is 0)");
      return 0;
   }

   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * RiskPercent / 100.0;

   double moneyPerLotStep = (slDistancePrice / tickSize) * tickValue * lotStep;
   if(moneyPerLotStep == 0)
   {
      Print(__FUNCTION__, ": moneyPerLotStep is 0");
      return 0;
   }

   double lots = MathFloor(riskMoney / moneyPerLotStep) * lotStep;
   lots = MathMax(minLot, MathMin(maxLot, lots));

   if(lots < minLot)
      return 0;

   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
//| Manage trailing stop for open positions                           |
//+------------------------------------------------------------------+
void ManageTrailingStop()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)MagicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      double posOpenPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double posSL        = PositionGetDouble(POSITION_SL);
      double posTP        = PositionGetDouble(POSITION_TP);
      long   posType      = PositionGetInteger(POSITION_TYPE);

      //--- Get current ATR for adaptive trailing
      double atrBuf[];
      ArraySetAsSeries(atrBuf, true);
      if(CopyBuffer(handleATR, 0, 0, 1, atrBuf) < 1) return;

      double trailDist = atrBuf[0] * TrailingStop_ATR_Mult;
      double trailStep = TrailingStep_Points * _Point;

      if(posType == POSITION_TYPE_BUY)
      {
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double newSL = NormalizeDouble(bid - trailDist, _Digits);

         //--- Only move SL up, never down; only when in profit
         if(newSL > posSL + trailStep && newSL > posOpenPrice)
         {
            if(!trade.PositionModify(ticket, newSL, posTP))
               Print("Trailing BUY modify failed | ", trade.ResultComment());
         }
      }
      else if(posType == POSITION_TYPE_SELL)
      {
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double newSL = NormalizeDouble(ask + trailDist, _Digits);

         //--- Only move SL down (tighter), never up; only when in profit
         if((posSL == 0 || newSL < posSL - trailStep) && newSL < posOpenPrice)
         {
            if(!trade.PositionModify(ticket, newSL, posTP))
               Print("Trailing SELL modify failed | ", trade.ResultComment());
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Safety: Check if spread is acceptable                             |
//+------------------------------------------------------------------+
bool IsSpreadAcceptable()
{
   int spread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > MaxSpreadPoints)
   {
      Print("Spread too high: ", spread, " > ", MaxSpreadPoints, " points");
      return false;
   }
   return true;
}

//+------------------------------------------------------------------+
//| Safety: Check if max positions reached                            |
//+------------------------------------------------------------------+
bool IsMaxPositionsReached()
{
   int count = CountMyPositions();
   return (count >= MaxOpenPositions);
}

//+------------------------------------------------------------------+
//| Safety: Check trading hours                                       |
//+------------------------------------------------------------------+
bool IsTradingHoursAllowed()
{
   MqlDateTime dt;
   TimeCurrent(dt);
   int hour = dt.hour;

   if(TradingStartHour < TradingEndHour)
      return (hour >= TradingStartHour && hour < TradingEndHour);
   else
      return (hour >= TradingStartHour || hour < TradingEndHour);
}

//+------------------------------------------------------------------+
//| Safety: Check daily loss limit                                    |
//+------------------------------------------------------------------+
bool IsDailyLossLimitHit()
{
   double currentBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   double dailyLoss = dailyStartBalance - currentBalance;
   double dailyLossPercent = (dailyStartBalance > 0) ? (dailyLoss / dailyStartBalance) * 100.0 : 0;

   if(dailyLossPercent >= DailyLossLimitPercent)
   {
      Print("Daily loss limit hit: ", DoubleToString(dailyLossPercent, 2),
            "% >= ", DoubleToString(DailyLossLimitPercent, 2), "%");
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Safety: Check cooldown between trades                             |
//+------------------------------------------------------------------+
bool IsCooldownActive()
{
   if(lastTradeBarTime == 0)
      return false;

   datetime currentBarTime = iTime(_Symbol, PERIOD_H1, 0);
   int barsPassed = Bars(_Symbol, PERIOD_H1, lastTradeBarTime, currentBarTime) - 1;

   if(barsPassed < MinBarsBetweenTrades)
      return true;

   return false;
}

//+------------------------------------------------------------------+
//| Reset daily tracking on new day                                   |
//+------------------------------------------------------------------+
void ResetDailyTracking()
{
   MqlDateTime dt;
   TimeCurrent(dt);

   if(dt.day_of_year != currentDay)
   {
      currentDay = dt.day_of_year;
      dailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      Print("New trading day detected. Daily start balance: ", DoubleToString(dailyStartBalance, 2));
   }
}

//+------------------------------------------------------------------+
//| Count positions belonging to this EA                              |
//+------------------------------------------------------------------+
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == (long)MagicNumber &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
      {
         count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Enforce broker minimum stop distance                              |
//+------------------------------------------------------------------+
double EnforceMinStopDistance(double price, double sl, bool isBuy)
{
   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * _Point;

   if(minDist <= 0)
      return sl;

   if(isBuy)
   {
      double minSL = NormalizeDouble(price - minDist, _Digits);
      if(sl > minSL)
         sl = minSL;
   }
   else
   {
      double minSL = NormalizeDouble(price + minDist, _Digits);
      if(sl < minSL)
         sl = minSL;
   }

   return sl;
}

//+------------------------------------------------------------------+
//| Get supported filling mode for this broker/symbol                 |
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING GetFillingMode()
{
   long fillMode = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);

   if((fillMode & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      return ORDER_FILLING_FOK;

   if((fillMode & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      return ORDER_FILLING_IOC;

   return ORDER_FILLING_RETURN;
}

//+------------------------------------------------------------------+
//| Restore state from existing positions after restart               |
//+------------------------------------------------------------------+
void RestoreStateFromPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)MagicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      datetime posTime = (datetime)PositionGetInteger(POSITION_TIME);
      if(posTime > lastTradeBarTime)
         lastTradeBarTime = posTime;
   }

   if(lastTradeBarTime > 0)
      Print("Restored state: last trade bar time = ", TimeToString(lastTradeBarTime));
}
//+------------------------------------------------------------------+
