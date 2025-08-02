from AlgorithmImports import *
import numpy as np

class OptimizedKOStockAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash
        self.SetCash(6319)
        
        # Add KO with optimized resolution
        self.ko = self.AddEquity("KO", Resolution.Minute).Symbol
        self.SetBenchmark(self.ko)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # OPTIMIZED Risk management parameters
        self.max_position_size = 0.75      # Reduced from 80% for better risk control
        self.base_stop_loss = 0.025        # Base stop loss
        self.base_take_profit = 0.045      # Base take profit
        self.trailing_stop_trigger = 0.02  # Start trailing at 2% profit
        self.min_trade_value = 350         # Slightly higher minimum
        self.max_trades_per_day = 2
        self.daily_trade_count = 0
        
        # OPTIMIZED Entry thresholds (backtested values)
        self.rsi_low = 40                  # Optimized from 35
        self.rsi_high = 65                 # Optimized from 70
        self.bb_multiplier = 1.015         # Optimized from 1.02
        self.macd_threshold = 0.995        # Optimized from 0.98
        self.volume_threshold = 0.8        # Optimized volume filter
        
        # Dynamic position sizing
        self.use_atr_sizing = True
        self.risk_per_trade = 0.015        # 1.5% risk per trade
        
        # Trade management
        self.entry_price = 0
        self.position_entry_time = None
        self.trailing_stop_price = 0
        self.min_hold_minutes = 45         # Optimized from 60
        self.market_regime = "NEUTRAL"
        
        # Performance tracking
        self.win_count = 0
        self.loss_count = 0
        self.total_trades = 0
        
        # Schedule daily reset
        self.Schedule.On(
            self.DateRules.EveryDay(self.ko), 
            self.TimeRules.AfterMarketOpen(self.ko, 5), 
            self.ResetDailyCounters
        )
        
        # Warm up
        self.SetWarmUp(50)
        
    def Setup_Indicators(self):
        # OPTIMIZED indicator periods (backtested)
        self.ema_fast = self.EMA(self.ko, 9, Resolution.Daily)      # Optimized from 8
        self.ema_slow = self.EMA(self.ko, 22, Resolution.Daily)     # Optimized from 21
        self.ema_trend = self.EMA(self.ko, 45, Resolution.Daily)    # Optimized from 50
        
        # RSI with optimized period
        self.rsi = self.RSI(self.ko, 18, Resolution.Daily)          # Optimized from 21
        
        # MACD with optimized settings
        self.macd = self.MACD(self.ko, 10, 24, 8, Resolution.Daily) # Optimized parameters
        
        # Bollinger Bands with optimized settings
        self.bb = self.BB(self.ko, 18, 2.1, Resolution.Daily)      # Optimized period and std
        
        # Volume with shorter period for responsiveness
        self.volume_sma = self.SMA(self.ko, 15, Resolution.Daily, Field.Volume)  # Optimized from 20
        
        # Long term trend
        self.sma_200 = self.SMA(self.ko, 200, Resolution.Daily)
        
        # ATR for dynamic position sizing
        self.atr = self.ATR(self.ko, 12, Resolution.Daily)          # Optimized from 14
        
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
            self.CheckOptimizedExitConditions(current_price, current_time)
        else:
            # Look for entry opportunities
            if self.daily_trade_count < self.max_trades_per_day:
                self.CheckOptimizedEntryConditions(current_price, current_time, data)
    
    def UpdateMarketRegime(self, current_price):
        """Optimized market regime detection"""
        if not self.sma_200.IsReady:
            return
            
        sma_200_value = self.sma_200.Current.Value
        ema_trend_value = self.ema_trend.Current.Value
        rsi_value = self.rsi.Current.Value
        
        # Multi-factor regime detection
        bullish_signals = 0
        bearish_signals = 0
        
        # Price vs long-term trend
        if current_price > sma_200_value * 1.015:  # Optimized threshold
            bullish_signals += 2
        elif current_price < sma_200_value * 0.985:
            bearish_signals += 2
            
        # Price vs medium-term trend
        if current_price > ema_trend_value * 1.005:  # Optimized threshold
            bullish_signals += 2
        elif current_price < ema_trend_value * 0.995:
            bearish_signals += 2
            
        # RSI momentum
        if rsi_value > 55:
            bullish_signals += 1
        elif rsi_value < 45:
            bearish_signals += 1
        
        # Set regime
        if bullish_signals >= 3 and bullish_signals > bearish_signals:
            self.market_regime = "BULLISH"
        elif bearish_signals >= 3 and bearish_signals > bullish_signals:
            self.market_regime = "BEARISH"
        else:
            self.market_regime = "NEUTRAL"
    
    def CalculateOptimalPositionSize(self, current_price):
        """Dynamic position sizing based on ATR"""
        if not self.use_atr_sizing or not self.atr.IsReady:
            # Fallback to traditional sizing
            available_capital = self.Portfolio.Cash
            max_trade_value = available_capital * self.max_position_size
            return int(max_trade_value / current_price)
        
        # ATR-based position sizing
        atr_value = self.atr.Current.Value
        risk_per_share = atr_value * 2.5  # 2.5x ATR as risk per share
        
        # Calculate shares based on risk tolerance
        portfolio_value = self.Portfolio.TotalPortfolioValue
        dollar_risk = portfolio_value * self.risk_per_trade
        optimal_shares = int(dollar_risk / risk_per_share)
        
        # Limit by available capital
        available_capital = self.Portfolio.Cash
        max_trade_value = available_capital * self.max_position_size
        max_shares_by_capital = int(max_trade_value / current_price)
        
        return min(optimal_shares, max_shares_by_capital)
    
    def CheckOptimizedEntryConditions(self, current_price, current_time, data):
        """Optimized entry conditions with backtested parameters"""
        
        # Get optimized indicator values
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
        
        # Optimized volume analysis
        current_volume = data[self.ko].Volume
        avg_volume = self.volume_sma.Current.Value
        volume_ok = current_volume > avg_volume * self.volume_threshold
        
        # Calculate optimal position size
        potential_shares = self.CalculateOptimalPositionSize(current_price)
        trade_value = potential_shares * current_price
        
        # Skip if trade too small
        if trade_value < self.min_trade_value:
            return
        
        # OPTIMIZED Long entry conditions
        long_conditions = [
            # Trend conditions (optimized thresholds)
            current_price > sma_200 * 1.005,                # Slightly above long-term
            ema_fast > ema_slow * 1.003,                     # Clear short-term uptrend
            current_price > ema_trend * 1.002,               # Above medium-term trend
            
            # Market regime
            self.market_regime in ["BULLISH", "NEUTRAL"],
            
            # Optimized momentum conditions
            rsi_value > self.rsi_low and rsi_value < self.rsi_high,  # 40-65 range
            macd_value > macd_signal * self.macd_threshold,           # 0.995 threshold
            
            # Optimized mean reversion
            current_price <= bb_middle * self.bb_multiplier,         # 1.015 multiplier
            current_price > bb_lower * 1.025,                        # Not oversold
            
            # Volume and timing
            volume_ok,
            current_time.hour >= 10 and current_time.hour < 15,
            trade_value >= self.min_trade_value,
            
            # Additional quality filter
            self.atr.Current.Value / current_price < 0.025   # Low volatility confirmation
        ]
        
        # OPTIMIZED Short entry conditions (more conservative)
        short_conditions = [
            current_price < sma_200 * 0.995,                # Below long-term
            ema_fast < ema_slow * 0.997,                     # Clear downtrend
            current_price < ema_trend * 0.998,               # Below trend
            self.market_regime == "BEARISH",                 # Only in bearish regime
            rsi_value < 60 and rsi_value > 35,               # Momentum range
            macd_value < macd_signal * 1.002,                # MACD bearish
            current_price >= bb_middle * 0.985,              # Near middle
            volume_ok,
            current_time.hour >= 10 and current_time.hour < 15
        ]
        
        # Execute trades with optimized thresholds
        if sum(long_conditions) >= 10:  # Increased threshold
            self.EnterOptimizedLongPosition(current_price, potential_shares)
        elif sum(short_conditions) >= 8:  # Conservative short threshold
            self.EnterOptimizedShortPosition(current_price, potential_shares)
    
    def EnterOptimizedLongPosition(self, entry_price, shares):
        """Enter long position with optimized parameters"""
        if shares > 0:
            self.MarketOrder(self.ko, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.trailing_stop_price = entry_price * (1 - self.base_stop_loss)
            self.daily_trade_count += 1
            self.total_trades += 1
            
            trade_value = shares * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"LONG KO (Optimized): {shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%)")
    
    def EnterOptimizedShortPosition(self, entry_price, shares):
        """Enter short position with optimized sizing"""
        short_shares = -int(shares * 0.6)  # More conservative short sizing
        
        if short_shares < 0:
            self.MarketOrder(self.ko, short_shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.trailing_stop_price = entry_price * (1 + self.base_stop_loss)
            self.daily_trade_count += 1
            self.total_trades += 1
            
            trade_value = abs(short_shares) * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"SHORT KO (Optimized): {short_shares} shares @ ${entry_price:.2f}")
    
    def CheckOptimizedExitConditions(self, current_price, current_time):
        """Optimized exit conditions with trailing stops and dynamic management"""
        position = self.Portfolio[self.ko]
        
        if position.Quantity == 0:
            return
            
        # Calculate P&L
        if position.IsLong:
            pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:
            pnl_pct = (self.entry_price - current_price) / self.entry_price
        
        # Time metrics
        minutes_held = (current_time - self.position_entry_time).total_seconds() / 60
        days_held = minutes_held / (60 * 24)
        
        # Exit conditions
        should_exit = False
        exit_reason = ""
        
        # OPTIMIZED Trailing stop logic
        if position.IsLong and pnl_pct >= self.trailing_stop_trigger:
            # Update trailing stop
            new_trailing_stop = current_price * (1 - self.base_stop_loss * 0.7)  # Tighter trailing
            if new_trailing_stop > self.trailing_stop_price:
                self.trailing_stop_price = new_trailing_stop
            
            # Check trailing stop
            if current_price <= self.trailing_stop_price:
                should_exit = True
                exit_reason = "TRAILING_STOP"
        
        # Standard profit target (optimized)
        if pnl_pct >= self.base_take_profit:
            should_exit = True
            exit_reason = "TAKE_PROFIT"
        
        # Standard stop loss
        elif pnl_pct <= -self.base_stop_loss:
            should_exit = True
            exit_reason = "STOP_LOSS"
        
        # OPTIMIZED Time-based exits
        elif minutes_held >= self.min_hold_minutes:
            
            # Quick profit taking (optimized)
            if pnl_pct >= 0.02 and days_held >= 0.5:  # 2% profit after half day
                should_exit = True
                exit_reason = "QUICK_PROFIT"
            
            # Trend reversal (optimized sensitivity)
            elif position.IsLong and self.ema_fast.Current.Value < self.ema_slow.Current.Value * 0.9995:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            elif position.IsShort and self.ema_fast.Current.Value > self.ema_slow.Current.Value * 1.0005:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            
            # RSI extremes (optimized levels)
            elif position.IsLong and self.rsi.Current.Value > 72:
                should_exit = True
                exit_reason = "RSI_OVERBOUGHT"
            elif position.IsShort and self.rsi.Current.Value < 28:
                should_exit = True
                exit_reason = "RSI_OVERSOLD"
            
            # Time-based profit scaling
            elif days_held >= 5 and pnl_pct > 0.01:  # 1% profit after 5 days
                should_exit = True
                exit_reason = "TIME_PROFIT_SCALING"
            
            # End of day
            elif current_time.hour >= 15 and current_time.minute >= 45:
                should_exit = True
                exit_reason = "END_OF_DAY"
        
        # Emergency stop (tighter)
        if pnl_pct <= -0.04:  # 4% emergency stop
            should_exit = True
            exit_reason = "EMERGENCY_STOP"
        
        # Execute exit
        if should_exit:
            self.Liquidate(self.ko)
            profit = pnl_pct * 100
            
            # Track win/loss
            if pnl_pct > 0:
                self.win_count += 1
            else:
                self.loss_count += 1
            
            # Calculate current win rate
            current_win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
            
            self.Log(f"EXIT KO ({exit_reason}): P&L = {profit:.2f}% | Win Rate: {current_win_rate:.1f}% ({self.win_count}/{self.total_trades})")
            
            # Reset
            self.entry_price = 0
            self.position_entry_time = None
            self.trailing_stop_price = 0
    
    def AllIndicatorsReady(self):
        """Check if indicators are ready"""
        indicators = [
            self.ema_fast, self.ema_slow, self.ema_trend,
            self.rsi, self.macd, self.bb, self.volume_sma,
            self.sma_200, self.atr
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Enhanced final performance log"""
        final_value = self.Portfolio.TotalPortfolioValue
        initial_value = 6319
        total_return = (final_value - initial_value) / initial_value * 100
        
        # Calculate final statistics
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        
        self.Log(f"=== OPTIMIZED KO ALGORITHM PERFORMANCE ===")
        self.Log(f"Initial Capital: ${initial_value:,.2f}")
        self.Log(f"Final Portfolio: ${final_value:,.2f}")
        self.Log(f"Total Return: {total_return:.2f}%")
        self.Log(f"Total Trades: {self.total_trades}")
        self.Log(f"Wins: {self.win_count} | Losses: {self.loss_count}")
        self.Log(f"Win Rate: {win_rate:.1f}%")
        self.Log(f"Profit: ${final_value - initial_value:,.2f}")