from AlgorithmImports import *
import numpy as np

class HighWinRateKOStockAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash
        self.SetCash(6319)
        
        # Add KO (Coca-Cola) 
        self.ko = self.AddEquity("KO", Resolution.Minute).Symbol
        
        # Set benchmark
        self.SetBenchmark(self.ko)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # Risk management parameters
        self.max_position_size = 0.80
        self.stop_loss_pct = 0.025
        self.take_profit_pct = 0.045
        self.min_trade_value = 300
        self.max_trades_per_day = 2
        self.daily_trade_count = 0
        
        # Trade management
        self.entry_price = 0
        self.position_entry_time = None
        self.min_hold_minutes = 60
        self.market_regime = "NEUTRAL"
        
        # Schedule daily reset
        self.Schedule.On(
            self.DateRules.EveryDay(self.ko), 
            self.TimeRules.AfterMarketOpen(self.ko, 5), 
            self.ResetDailyCounters
        )
        
        # Warm up
        self.SetWarmUp(50)
        
    def Setup_Indicators(self):
        # Trend indicators
        self.ema_fast = self.EMA(self.ko, 8, Resolution.Daily)
        self.ema_slow = self.EMA(self.ko, 21, Resolution.Daily)
        self.ema_trend = self.EMA(self.ko, 50, Resolution.Daily)
        
        # RSI for momentum
        self.rsi = self.RSI(self.ko, 21, Resolution.Daily)
        
        # MACD for trend confirmation
        self.macd = self.MACD(self.ko, 12, 26, 9, Resolution.Daily)
        
        # Bollinger Bands
        self.bb = self.BB(self.ko, 20, 2, Resolution.Daily)
        
        # Volume
        self.volume_sma = self.SMA(self.ko, 20, Resolution.Daily, Field.Volume)
        
        # Long term trend
        self.sma_200 = self.SMA(self.ko, 200, Resolution.Daily)
        
        # ATR for volatility
        self.atr = self.ATR(self.ko, 14, Resolution.Daily)
        
    def ResetDailyCounters(self):
        """Reset daily trade counter"""
        self.daily_trade_count = 0
        
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        if not self.AllIndicatorsReady():
            return
            
        if not data.ContainsKey(self.ko):
            return
            
        current_price = data[self.ko].Close
        current_time = self.Time
        
        # Update market regime
        self.UpdateMarketRegime(current_price)
        
        # Check for exit conditions first
        if self.Portfolio[self.ko].Invested:
            self.CheckExitConditions(current_price, current_time)
        else:
            # Look for entry opportunities
            if self.daily_trade_count < self.max_trades_per_day:
                self.CheckEntryConditions(current_price, current_time, data)
    
    def UpdateMarketRegime(self, current_price):
        """Simple market regime detection"""
        if not self.sma_200.IsReady:
            return
            
        sma_200_value = self.sma_200.Current.Value
        ema_50_value = self.ema_trend.Current.Value
        
        if current_price > sma_200_value * 1.02 and current_price > ema_50_value:
            self.market_regime = "BULLISH"
        elif current_price < sma_200_value * 0.98 and current_price < ema_50_value:
            self.market_regime = "BEARISH"
        else:
            self.market_regime = "NEUTRAL"
    
    def CheckEntryConditions(self, current_price, current_time, data):
        """Entry conditions for KO"""
        
        # Basic indicator values
        rsi_value = self.rsi.Current.Value
        macd_value = self.macd.Current.Value
        macd_signal = self.macd.Signal.Current.Value
        ema_fast = self.ema_fast.Current.Value
        ema_slow = self.ema_slow.Current.Value
        ema_trend = self.ema_trend.Current.Value
        bb_upper = self.bb.UpperBand.Current.Value
        bb_lower = self.bb.LowerBand.Current.Value
        bb_middle = self.bb.MiddleBand.Current.Value
        sma_200 = self.sma_200.Current.Value
        
        # Volume analysis
        current_volume = data[self.ko].Volume
        avg_volume = self.volume_sma.Current.Value
        volume_ok = current_volume > avg_volume * 0.7
        
        # Calculate potential trade size
        available_capital = self.Portfolio.Cash
        max_trade_value = available_capital * self.max_position_size
        potential_shares = int(max_trade_value / current_price)
        trade_value = potential_shares * current_price
        
        # Skip if trade too small
        if trade_value < self.min_trade_value:
            return
        
        # Long entry conditions
        long_conditions = [
            current_price > sma_200,                    # Above long-term trend
            ema_fast > ema_slow,                        # Short-term uptrend
            current_price > ema_trend,                  # Above medium-term trend
            self.market_regime in ["BULLISH", "NEUTRAL"], # Favorable regime
            rsi_value > 35 and rsi_value < 70,          # Reasonable momentum
            macd_value > macd_signal * 0.98,            # MACD positive
            current_price <= bb_middle * 1.02,          # Not extended
            current_price > bb_lower * 1.03,            # Not oversold
            volume_ok,                                  # Volume confirmation
            current_time.hour >= 10 and current_time.hour < 15,  # Time filter
            trade_value >= self.min_trade_value         # Size check
        ]
        
        # Short entry conditions (conservative)
        short_conditions = [
            current_price < sma_200 * 0.98,             # Below long-term
            ema_fast < ema_slow,                        # Downtrend
            current_price < ema_trend * 0.99,           # Below trend
            self.market_regime == "BEARISH",            # Bearish regime
            rsi_value < 65 and rsi_value > 30,          # Not extreme
            macd_value < macd_signal,                   # MACD negative
            current_price >= bb_middle * 0.98,          # Near middle
            volume_ok,                                  # Volume
            current_time.hour >= 10 and current_time.hour < 15  # Time
        ]
        
        # Execute trades
        if sum(long_conditions) >= 9:  # High threshold
            self.EnterLongPosition(current_price, potential_shares)
        elif sum(short_conditions) >= 8:  # Conservative short
            self.EnterShortPosition(current_price, potential_shares)
    
    def EnterLongPosition(self, entry_price, shares):
        """Enter long position"""
        if shares > 0:
            self.MarketOrder(self.ko, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = shares * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"LONG KO: {shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%)")
    
    def EnterShortPosition(self, entry_price, shares):
        """Enter short position (conservative)"""
        short_shares = -int(shares * 0.7)  # Smaller short size
        
        if short_shares < 0:
            self.MarketOrder(self.ko, short_shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = abs(short_shares) * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"SHORT KO: {short_shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%)")
    
    def CheckExitConditions(self, current_price, current_time):
        """Exit conditions"""
        position = self.Portfolio[self.ko]
        
        if position.Quantity == 0:
            return
            
        # Calculate P&L
        if position.IsLong:
            pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:
            pnl_pct = (self.entry_price - current_price) / self.entry_price
        
        # Time held
        minutes_held = (current_time - self.position_entry_time).total_seconds() / 60
        days_held = minutes_held / (60 * 24)
        
        # Exit conditions
        should_exit = False
        exit_reason = ""
        
        # Take profit
        if pnl_pct >= self.take_profit_pct:
            should_exit = True
            exit_reason = "TAKE_PROFIT"
        
        # Stop loss
        elif pnl_pct <= -self.stop_loss_pct:
            should_exit = True
            exit_reason = "STOP_LOSS"
        
        # Time-based exits
        elif minutes_held >= self.min_hold_minutes:
            
            # Trend reversal
            if position.IsLong and self.ema_fast.Current.Value < self.ema_slow.Current.Value:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            elif position.IsShort and self.ema_fast.Current.Value > self.ema_slow.Current.Value:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            
            # RSI extremes
            elif position.IsLong and self.rsi.Current.Value > 75:
                should_exit = True
                exit_reason = "RSI_OVERBOUGHT"
            elif position.IsShort and self.rsi.Current.Value < 25:
                should_exit = True
                exit_reason = "RSI_OVERSOLD"
            
            # End of day
            elif current_time.hour >= 15 and current_time.minute >= 45:
                should_exit = True
                exit_reason = "END_OF_DAY"
        
        # Emergency stop
        if pnl_pct <= -0.05:  # 5% emergency
            should_exit = True
            exit_reason = "EMERGENCY_STOP"
        
        # Execute exit
        if should_exit:
            self.Liquidate(self.ko)
            profit = pnl_pct * 100
            trade_pnl = position.Quantity * (current_price - self.entry_price) if position.IsLong else position.Quantity * (self.entry_price - current_price)
            
            self.Log(f"EXIT KO ({exit_reason}): P&L = {profit:.2f}% (${trade_pnl:.2f}) after {days_held:.1f} days")
            
            # Reset
            self.entry_price = 0
            self.position_entry_time = None
    
    def AllIndicatorsReady(self):
        """Check if indicators are ready"""
        indicators = [
            self.ema_fast, self.ema_slow, self.ema_trend,
            self.rsi, self.macd, self.bb, self.volume_sma,
            self.sma_200, self.atr
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Final performance log"""
        final_value = self.Portfolio.TotalPortfolioValue
        initial_value = 6319
        total_return = (final_value - initial_value) / initial_value * 100
        
        self.Log(f"=== KO ALGORITHM PERFORMANCE ===")
        self.Log(f"Initial: ${initial_value:,.2f}")
        self.Log(f"Final: ${final_value:,.2f}")
        self.Log(f"Return: {total_return:.2f}%")