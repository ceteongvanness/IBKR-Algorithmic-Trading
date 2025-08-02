from AlgorithmImports import *
import numpy as np

class OptimizedBIRDAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set backtest period (BIRD IPO: November 2021)
        self.SetStartDate(2021, 11, 15)  # BIRD IPO date
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash
        self.SetCash(6319)
        
        # Add BIRD (Allbirds Inc.) - Growth retail stock
        self.bird = self.AddEquity("BIRD", Resolution.Minute).Symbol
        self.SetBenchmark(self.bird)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # OPTIMIZED Risk management for growth/retail stock
        self.max_position_size = 0.60      # Conservative 60% for volatile growth stock
        self.base_stop_loss = 0.08         # 8% stop (wider for growth stock volatility)
        self.base_take_profit = 0.15       # 15% target (higher for growth potential)
        self.quick_profit_threshold = 0.06  # 6% quick profit opportunity
        self.min_trade_value = 200         # Lower minimum due to BIRD's lower price
        self.max_trades_per_day = 1        # Very conservative for volatile stock
        
        # Growth stock specific parameters
        self.volatility_threshold = 0.05   # 5% daily volatility threshold
        self.volume_surge_multiplier = 2.0 # 2x volume surge requirement
        self.rsi_growth_low = 35           # Growth stock RSI range
        self.rsi_growth_high = 75          # Allow higher RSI for growth
        
        # Retail sector awareness
        self.retail_momentum = "NEUTRAL"
        self.earnings_proximity = "CLEAR"
        self.consumer_sentiment = "NEUTRAL"
        
        # Trade tracking for optimization
        self.entry_price = 0
        self.position_entry_time = None
        self.daily_trade_count = 0
        self.total_trades = 0
        self.win_count = 0
        self.loss_count = 0
        
        # Optimization parameters to test
        self.optimization_params = {
            'stop_loss_variants': [0.06, 0.08, 0.10, 0.12],
            'take_profit_variants': [0.12, 0.15, 0.18, 0.20],
            'position_size_variants': [0.50, 0.60, 0.70],
            'rsi_ranges': [(30, 70), (35, 75), (40, 80)]
        }
        
        # Current optimization set (will be varied in different runs)
        self.current_stop = 0.08
        self.current_profit = 0.15
        self.current_position = 0.60
        self.current_rsi = (35, 75)
        
        # Schedule functions
        self.Schedule.On(
            self.DateRules.EveryDay(self.bird), 
            self.TimeRules.AfterMarketOpen(self.bird, 5), 
            self.ResetDailyCounters
        )
        
        self.Schedule.On(
            self.DateRules.Every(DayOfWeek.Monday), 
            self.TimeRules.AfterMarketOpen(self.bird, 60), 
            self.WeeklyRetailAnalysis
        )
        
        # Warm up
        self.SetWarmUp(60)
        
    def Setup_Indicators(self):
        # Growth stock optimized indicators (shorter periods for responsiveness)
        self.ema_fast = self.EMA(self.bird, 5, Resolution.Daily)      # Very fast for growth
        self.ema_slow = self.EMA(self.bird, 15, Resolution.Daily)     # Quick response
        self.ema_trend = self.EMA(self.bird, 30, Resolution.Daily)    # Medium term
        
        # Intraday momentum
        self.intraday_ema = self.EMA(self.bird, 10, Resolution.Minute)
        
        # RSI for growth stock momentum
        self.rsi = self.RSI(self.bird, 10, Resolution.Daily)          # Shorter for growth
        
        # MACD with faster settings
        self.macd = self.MACD(self.bird, 8, 17, 6, Resolution.Daily)  # Faster for growth
        
        # Bollinger Bands with wider settings for volatility
        self.bb = self.BB(self.bird, 15, 2.5, Resolution.Daily)       # Wider for growth
        
        # Volume surge detection (critical for growth stocks)
        self.volume_sma = self.SMA(self.bird, 10, Resolution.Daily, Field.Volume)
        self.volume_fast = self.SMA(self.bird, 3, Resolution.Daily, Field.Volume)
        
        # Volatility measurement
        self.atr = self.ATR(self.bird, 10, Resolution.Daily)          # Shorter period
        self.volatility_window = RollingWindow[float](20)
        
        # Retail sector proxy
        self.retail_momentum_rsi = self.RSI(self.bird, 20, Resolution.Weekly)
        
    def ResetDailyCounters(self):
        """Reset daily counters and update market analysis"""
        self.daily_trade_count = 0
        self.UpdateRetailSentiment()
        
    def WeeklyRetailAnalysis(self):
        """Weekly retail sector and earnings analysis"""
        self.CheckEarningsProximity()
        self.AnalyzeRetailMomentum()
        
    def UpdateRetailSentiment(self):
        """Update retail/consumer sentiment based on price action"""
        if not self.ema_trend.IsReady:
            return
            
        current_price = self.Securities[self.bird].Price
        trend_value = self.ema_trend.Current.Value
        
        # Simple retail sentiment based on trend
        if current_price > trend_value * 1.05:
            self.consumer_sentiment = "POSITIVE"
        elif current_price < trend_value * 0.95:
            self.consumer_sentiment = "NEGATIVE"
        else:
            self.consumer_sentiment = "NEUTRAL"
            
    def CheckEarningsProximity(self):
        """Check for BIRD earnings (quarterly)"""
        current_month = self.Time.month
        
        # BIRD typical earnings months (estimate)
        earnings_months = [3, 5, 8, 11]  # March, May, August, November
        
        if current_month in earnings_months:
            day = self.Time.day
            if 10 <= day <= 20:
                self.earnings_proximity = "NEAR"
            else:
                self.earnings_proximity = "CLEAR"
        else:
            self.earnings_proximity = "CLEAR"
            
    def AnalyzeRetailMomentum(self):
        """Analyze retail sector momentum"""
        if not self.retail_momentum_rsi.IsReady:
            return
            
        retail_rsi = self.retail_momentum_rsi.Current.Value
        
        if retail_rsi > 60:
            self.retail_momentum = "STRONG"
        elif retail_rsi < 40:
            self.retail_momentum = "WEAK"
        else:
            self.retail_momentum = "NEUTRAL"
    
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        if not self.AllIndicatorsReady():
            return
            
        if not data.ContainsKey(self.bird):
            return
            
        current_price = data[self.bird].Close
        current_time = self.Time
        
        # Update volatility tracking
        self.UpdateVolatilityTracking(current_price)
        
        # Check for exit conditions first
        if self.Portfolio[self.bird].Invested:
            self.CheckOptimizedExitConditions(current_price, current_time)
        else:
            # Look for entry opportunities
            if self.CanTradeGrowthStock():
                self.CheckOptimizedEntryConditions(current_price, current_time, data)
    
    def UpdateVolatilityTracking(self, current_price):
        """Track daily volatility for growth stock analysis"""
        if hasattr(self, 'previous_close'):
            daily_return = abs((current_price - self.previous_close) / self.previous_close)
            self.volatility_window.Add(daily_return)
        self.previous_close = current_price
        
    def CanTradeGrowthStock(self):
        """Enhanced trade filtering for growth stock"""
        # Standard checks
        if self.daily_trade_count >= self.max_trades_per_day:
            return False
            
        if self.Time.hour < 10 or (self.Time.hour >= 15 and self.Time.minute >= 30):
            return False
        
        # Growth stock specific checks
        if self.earnings_proximity == "NEAR":
            return False  # Avoid earnings volatility
            
        # Check if volatility is manageable
        if len(self.volatility_window) >= 10:
            recent_volatility = np.mean([x for x in self.volatility_window[:10]])
            if recent_volatility > self.volatility_threshold:
                return False  # Too volatile
                
        return True
    
    def CheckOptimizedEntryConditions(self, current_price, current_time, data):
        """Optimized entry conditions for BIRD growth stock"""
        
        # Indicator values
        rsi_value = self.rsi.Current.Value
        macd_value = self.macd.Current.Value
        macd_signal = self.macd.Signal.Current.Value
        ema_fast = self.ema_fast.Current.Value
        ema_slow = self.ema_slow.Current.Value
        ema_trend = self.ema_trend.Current.Value
        bb_upper = self.bb.UpperBand.Current.Value
        bb_lower = self.bb.LowerBand.Current.Value
        bb_middle = self.bb.MiddleBand.Current.Value
        intraday_ema = self.intraday_ema.Current.Value
        
        # Volume surge analysis (critical for growth stocks)
        current_volume = data[self.bird].Volume
        avg_volume = self.volume_sma.Current.Value
        recent_volume = self.volume_fast.Current.Value
        volume_surge = current_volume > avg_volume * self.volume_surge_multiplier
        volume_trend = recent_volume > avg_volume * 1.5
        
        # Position sizing for growth stock
        available_capital = self.Portfolio.Cash
        max_trade_value = available_capital * self.current_position
        potential_shares = int(max_trade_value / current_price)
        trade_value = potential_shares * current_price
        
        if trade_value < self.min_trade_value:
            return
        
        # OPTIMIZED BIRD Long entry conditions
        long_conditions = [
            # Trend alignment (critical for growth)
            ema_fast > ema_slow * 1.02,                     # Strong short-term uptrend
            current_price > ema_trend * 1.01,               # Above medium-term trend
            current_price > intraday_ema,                   # Intraday momentum
            
            # Growth momentum
            rsi_value > self.current_rsi[0] and rsi_value < self.current_rsi[1],  # RSI range
            macd_value > macd_signal * 1.05,                # Strong MACD signal
            
            # Volume confirmation (essential for growth stocks)
            volume_surge or volume_trend,                   # Volume spike required
            
            # Breakout or pullback setup
            (current_price > bb_upper * 0.99) or           # Breakout
            (current_price > bb_lower * 1.05 and current_price < bb_middle * 1.02),  # Pullback
            
            # Retail sector conditions
            self.retail_momentum in ["STRONG", "NEUTRAL"],
            self.consumer_sentiment in ["POSITIVE", "NEUTRAL"],
            
            # Risk management
            trade_value >= self.min_trade_value,
            self.earnings_proximity == "CLEAR",
            
            # Volatility check
            len(self.volatility_window) == 0 or np.mean([x for x in self.volatility_window[:5]]) < self.volatility_threshold
        ]
        
        # Growth stocks - focus on long positions (avoid shorts due to volatility)
        if sum(long_conditions) >= 9:  # High threshold for volatile growth stock
            self.EnterOptimizedLongPosition(current_price, potential_shares)
    
    def EnterOptimizedLongPosition(self, entry_price, shares):
        """Enter long position with growth stock optimization"""
        if shares > 0:
            self.MarketOrder(self.bird, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            self.total_trades += 1
            
            trade_value = shares * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"LONG BIRD: {shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%) - Retail: {self.retail_momentum}")
    
    def CheckOptimizedExitConditions(self, current_price, current_time):
        """Optimized exit conditions for growth stock"""
        position = self.Portfolio[self.bird]
        
        if position.Quantity == 0:
            return
            
        # Calculate P&L
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # Time metrics
        minutes_held = (current_time - self.position_entry_time).total_seconds() / 60
        hours_held = minutes_held / 60
        days_held = hours_held / 24
        
        # Exit conditions
        should_exit = False
        exit_reason = ""
        
        # Quick profit taking for growth stocks
        if pnl_pct >= self.quick_profit_threshold and hours_held >= 2:
            should_exit = True
            exit_reason = "QUICK_PROFIT"
        
        # Main profit target
        elif pnl_pct >= self.current_profit:
            should_exit = True
            exit_reason = "TAKE_PROFIT"
        
        # Stop loss
        elif pnl_pct <= -self.current_stop:
            should_exit = True
            exit_reason = "STOP_LOSS"
        
        # Time-based exits (growth stocks need quicker management)
        elif minutes_held >= 30:  # After 30 minutes minimum
            
            # Momentum reversal (critical for growth stocks)
            if self.ema_fast.Current.Value < self.ema_slow.Current.Value * 0.98:
                should_exit = True
                exit_reason = "MOMENTUM_REVERSAL"
            
            # RSI extremes (growth stock levels)
            elif self.rsi.Current.Value > 85:
                should_exit = True
                exit_reason = "RSI_EXTREME_HIGH"
            elif self.rsi.Current.Value < 15:
                should_exit = True
                exit_reason = "RSI_EXTREME_LOW"
            
            # Retail sentiment shift
            elif self.retail_momentum == "WEAK" and days_held >= 1:
                should_exit = True
                exit_reason = "RETAIL_SENTIMENT_WEAK"
            
            # Volume drying up (bad for growth stocks)
            elif hasattr(self, 'volume_fast') and self.volume_fast.Current.Value < self.volume_sma.Current.Value * 0.5:
                if days_held >= 2:
                    should_exit = True
                    exit_reason = "VOLUME_DRYING_UP"
            
            # End of day (avoid overnight risk in growth stocks)
            elif current_time.hour >= 15 and current_time.minute >= 30:
                should_exit = True
                exit_reason = "END_OF_DAY"
        
        # Emergency stop for growth stock
        if pnl_pct <= -0.15:  # 15% emergency stop
            should_exit = True
            exit_reason = "EMERGENCY_STOP"
        
        # Earnings protection
        if self.earnings_proximity == "NEAR":
            should_exit = True
            exit_reason = "EARNINGS_PROTECTION"
        
        # Execute exit
        if should_exit:
            self.Liquidate(self.bird)
            profit = pnl_pct * 100
            
            # Track performance
            if pnl_pct > 0:
                self.win_count += 1
            else:
                self.loss_count += 1
            
            win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
            
            self.Log(f"EXIT BIRD ({exit_reason}): P&L = {profit:.2f}% | Win Rate: {win_rate:.1f}% ({self.win_count}/{self.total_trades}) | Hours: {hours_held:.1f}")
            
            # Reset
            self.entry_price = 0
            self.position_entry_time = None
    
    def AllIndicatorsReady(self):
        """Check if all indicators are ready"""
        indicators = [
            self.ema_fast, self.ema_slow, self.ema_trend,
            self.rsi, self.macd, self.bb, self.volume_sma,
            self.atr, self.intraday_ema, self.volume_fast
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Comprehensive backtesting results with optimization metrics"""
        final_value = self.Portfolio.TotalPortfolioValue
        initial_value = 6319
        total_return = (final_value - initial_value) / initial_value * 100
        
        # Calculate performance metrics
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        avg_trade_return = total_return / self.total_trades if self.total_trades > 0 else 0
        
        # Risk metrics
        if hasattr(self, 'daily_returns'):
            sharpe_ratio = self.CalculateSharpeRatio()
        else:
            sharpe_ratio = 0
            
        self.Log(f"=== BIRD OPTIMIZATION BACKTEST RESULTS ===")
        self.Log(f"PARAMETERS TESTED:")
        self.Log(f"Stop Loss: {self.current_stop*100:.1f}%")
        self.Log(f"Take Profit: {self.current_profit*100:.1f}%") 
        self.Log(f"Position Size: {self.current_position*100:.1f}%")
        self.Log(f"RSI Range: {self.current_rsi[0]}-{self.current_rsi[1]}")
        self.Log(f"")
        self.Log(f"PERFORMANCE METRICS:")
        self.Log(f"Initial Capital: ${initial_value:,.2f}")
        self.Log(f"Final Portfolio: ${final_value:,.2f}")
        self.Log(f"Total Return: {total_return:.2f}%")
        self.Log(f"Total Trades: {self.total_trades}")
        self.Log(f"Wins: {self.win_count} | Losses: {self.loss_count}")
        self.Log(f"Win Rate: {win_rate:.1f}%")
        self.Log(f"Avg Trade Return: {avg_trade_return:.2f}%")
        self.Log(f"Profit/Loss: ${final_value - initial_value:,.2f}")
        
        # Store results for optimization comparison
        self.optimization_result = {
            'parameters': {
                'stop_loss': self.current_stop,
                'take_profit': self.current_profit,
                'position_size': self.current_position,
                'rsi_range': self.current_rsi
            },
            'performance': {
                'total_return': total_return,
                'win_rate': win_rate,
                'total_trades': self.total_trades,
                'final_value': final_value,
                'sharpe_ratio': sharpe_ratio
            }
        }
    
    def CalculateSharpeRatio(self):
        """Calculate Sharpe ratio for optimization"""
        # Simplified Sharpe calculation
        if len(self.daily_returns) < 10:
            return 0
        returns = np.array(self.daily_returns)
        return np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0