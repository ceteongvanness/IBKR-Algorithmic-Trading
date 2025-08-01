from AlgorithmImports import *
import numpy as np

class HighWinRateOStockAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash - optimized for smaller account
        self.SetCash(6319)  # Your current capital
        
        # Add O (Realty Income Corporation) - "The Monthly Dividend Company"
        self.o = self.AddEquity("O", Resolution.Minute).Symbol
        
        # Set benchmark to O
        self.SetBenchmark(self.o)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # Risk management parameters (optimized for REIT small account)
        self.max_position_size = 0.80       # 80% max position (conservative for REIT)
        self.stop_loss_pct = 0.04          # 4% stop loss (wider for REIT volatility)
        self.take_profit_pct = 0.06        # 6% take profit (higher for stable REIT)
        
        # Small account optimizations for monthly dividend REIT
        self.min_trade_value = 350         # Minimum $350 per trade (O around $50-60)
        self.max_trades_per_day = 2        # Conservative for REIT trading
        self.daily_trade_count = 0
        
        # Monthly dividend tracking
        self.monthly_dividend_schedule = self.InitializeMonthlyDividendSchedule()
        self.dividend_boost_active = False
        self.last_ex_dividend_month = 0
        
        # Trade management
        self.entry_price = 0
        self.position_entry_time = None
        self.min_hold_minutes = 90         # Longer holds for REIT (less liquid)
        self.max_hold_days = 21            # Maximum hold for mean reversion
        
        # Market regime detection
        self.market_regime = "NEUTRAL"
        self.reit_sector_strength = "NEUTRAL"
        self.interest_rate_environment = "NEUTRAL"
        
        # Schedule functions
        self.Schedule.On(self.DateRules.EveryDay(self.o), 
                        self.TimeRules.AfterMarketOpen(self.o, 30), 
                        self.CheckMarketRegime)
        
        self.Schedule.On(self.DateRules.EveryDay(self.o), 
                        self.TimeRules.AfterMarketOpen(self.o, 5), 
                        self.ResetDailyCounters)
        
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday), 
                        self.TimeRules.AfterMarketOpen(self.o, 60), 
                        self.CheckMonthlyDividendSchedule)
        
        # Warm up period
        self.SetWarmUp(150)
        
    def Setup_Indicators(self):
        # Trend indicators (optimized for REIT characteristics)
        self.ema_fast = self.EMA(self.o, 10, Resolution.Daily)    # Short term REIT trend
        self.ema_slow = self.EMA(self.o, 25, Resolution.Daily)    # Medium term
        self.ema_trend = self.EMA(self.o, 50, Resolution.Daily)   # Long term REIT trend
        
        # Higher timeframe for stability
        self.sma_200 = self.SMA(self.o, 200, Resolution.Daily)    # Long-term REIT health
        
        # RSI for momentum (longer period for REIT stability)
        self.rsi = self.RSI(self.o, 25, Resolution.Daily)
        
        # MACD for trend confirmation
        self.macd = self.MACD(self.o, 12, 26, 9, Resolution.Daily)
        
        # Bollinger Bands for volatility and mean reversion
        self.bb = self.BB(self.o, 20, 2.5, Resolution.Daily)  # Wider bands for REIT
        
        # Volume indicators (REITs typically lower volume)
        self.volume_sma = self.SMA(self.o, 30, Resolution.Daily, Field.Volume)
        
        # ATR for volatility measurement
        self.atr = self.ATR(self.o, 21, Resolution.Daily)     # Longer period for REIT
        
        # Interest rate proxy (using inverse relationship)
        self.interest_rate_proxy = RollingWindow[float](60)
        
        # REIT sector strength (using O's own momentum as proxy)
        self.reit_momentum = self.RSI(self.o, 50, Resolution.Weekly)
        
    def InitializeMonthlyDividendSchedule(self):
        """Initialize O's monthly dividend schedule"""
        return {
            'frequency': 'monthly',
            'typical_declaration_day': 15,  # Usually mid-month
            'ex_dividend_offset': 10,       # Days after declaration
            'payment_offset': 15,           # Days after ex-dividend
            'boost_period_days': 7          # Days before ex-dividend for boost
        }
        
    def ResetDailyCounters(self):
        """Reset daily trade counter"""
        self.daily_trade_count = 0
        
    def CheckMonthlyDividendSchedule(self):
        """Check monthly dividend schedule for O"""
        current_day = self.Time.day
        current_month = self.Time.month
        
        # Check if we're in a new month (reset tracking)
        if current_month != self.last_ex_dividend_month:
            self.last_ex_dividend_month = current_month
            
            # Activate dividend boost in last week of each month
            if 20 <= current_day <= 31:
                self.dividend_boost_active = True
                self.Log(f"Monthly dividend boost activated for O in month {current_month}")
            else:
                self.dividend_boost_active = False
        else:
            # Check if still in boost period
            if 20 <= current_day <= 31:
                self.dividend_boost_active = True
            else:
                self.dividend_boost_active = False
                
    def CheckMarketRegime(self):
        """Determine market regime for O (REIT-specific factors)"""
        if not self.sma_200.IsReady:
            return
            
        current_price = self.Securities[self.o].Price
        sma_200_value = self.sma_200.Current.Value
        ema_50_value = self.ema_trend.Current.Value
        
        # Update interest rate proxy (inverse price relationship)
        if current_price > 0:
            self.interest_rate_proxy.Add(1.0 / current_price)
        
        # REIT regime detection (interest rate sensitive)
        bullish_signals = 0
        bearish_signals = 0
        
        # Long-term REIT health (critical for dividend sustainability)
        if current_price > sma_200_value * 1.02:
            bullish_signals += 3
        elif current_price < sma_200_value * 0.98:
            bearish_signals += 3
            
        # Medium-term trend
        if current_price > ema_50_value * 1.01:
            bullish_signals += 2
        elif current_price < ema_50_value * 0.99:
            bearish_signals += 2
            
        # REIT sector momentum
        if self.reit_momentum.IsReady:
            reit_rsi = self.reit_momentum.Current.Value
            if reit_rsi > 55:
                bullish_signals += 2
                self.reit_sector_strength = "STRONG"
            elif reit_rsi < 45:
                bearish_signals += 2
                self.reit_sector_strength = "WEAK"
            else:
                self.reit_sector_strength = "NEUTRAL"
        
        # Interest rate environment (simplified proxy)
        if len(self.interest_rate_proxy) >= 30:
            recent_avg = np.mean([x for x in self.interest_rate_proxy[:30]])
            older_avg = np.mean([x for x in self.interest_rate_proxy[30:60]]) if len(self.interest_rate_proxy) >= 60 else recent_avg
            
            if recent_avg > older_avg * 1.02:  # Price rising (rates falling - good for REITs)
                bullish_signals += 1
                self.interest_rate_environment = "FAVORABLE"
            elif recent_avg < older_avg * 0.98:  # Price falling (rates rising - bad for REITs)
                bearish_signals += 1
                self.interest_rate_environment = "UNFAVORABLE"
            else:
                self.interest_rate_environment = "NEUTRAL"
        
        # Set market regime
        if bullish_signals >= 5 and bullish_signals > bearish_signals:
            self.market_regime = "BULLISH"
        elif bearish_signals >= 5 and bearish_signals > bullish_signals:
            self.market_regime = "BEARISH"
        else:
            self.market_regime = "NEUTRAL"
    
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        if not self.AllIndicatorsReady():
            return
            
        if not data.ContainsKey(self.o):
            return
            
        current_price = data[self.o].Close
        current_time = self.Time
        
        # Check for exit conditions first
        if self.Portfolio[self.o].Invested:
            self.CheckExitConditions(current_price, current_time)
        else:
            # Look for entry opportunities
            if self.daily_trade_count < self.max_trades_per_day:
                self.CheckEntryConditions(current_price, current_time, data)
    
    def CheckEntryConditions(self, current_price, current_time, data):
        """Entry conditions optimized for O (monthly dividend REIT)"""
        
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
        
        # Volume analysis (REITs typically lower volume)
        current_volume = data[self.o].Volume
        avg_volume = self.volume_sma.Current.Value
        volume_adequate = current_volume > avg_volume * 0.6  # Lower threshold for REIT
        
        # Calculate potential trade size
        available_capital = self.Portfolio.Cash
        max_trade_value = available_capital * self.max_position_size
        potential_shares = int(max_trade_value / current_price)
        trade_value = potential_shares * current_price
        
        # Skip if trade too small
        if trade_value < self.min_trade_value:
            return
        
        # O Long entry conditions (monthly dividend REIT approach)
        long_conditions = [
            # REIT dividend sustainability
            current_price > sma_200 * 0.98,  # Near long-term support
            
            # Trend alignment
            ema_fast > ema_slow * 0.998,     # Slight uptrend sufficient
            current_price > ema_trend * 0.99, # Near trend line
            
            # Market regime favorable for REITs
            self.market_regime in ["BULLISH", "NEUTRAL"],
            
            # REIT sector not weak
            self.reit_sector_strength in ["STRONG", "NEUTRAL"],
            
            # Interest rate environment
            self.interest_rate_environment in ["FAVORABLE", "NEUTRAL"],
            
            # Conservative momentum (REITs move slower)
            rsi_value > 30 and rsi_value < 75,
            
            # MACD trend (less strict for REIT)
            macd_value > macd_signal * 0.90,
            
            # Mean reversion opportunity
            current_price <= bb_middle * 1.03,
            current_price > bb_lower * 1.02,
            
            # Volume adequate for REIT
            volume_adequate,
            
            # Time filter (REITs less time-sensitive)
            current_time.hour >= 10 and current_time.hour < 15,
            
            # Trade size validation
            trade_value >= self.min_trade_value
        ]
        
        # Monthly dividend boost condition
        if self.dividend_boost_active:
            long_conditions.append(True)  # Extra boost near monthly dividend
        
        # Short entry conditions (very conservative for dividend REIT)
        short_conditions = [
            # Significant REIT sector weakness
            current_price < sma_200 * 0.95,
            
            # Clear downtrend
            ema_fast < ema_slow * 0.995,
            current_price < ema_trend * 0.97,
            
            # Market regime bearish
            self.market_regime == "BEARISH",
            
            # REIT sector weakness
            self.reit_sector_strength == "WEAK",
            
            # Unfavorable interest rate environment
            self.interest_rate_environment == "UNFAVORABLE",
            
            # Momentum confirmation
            rsi_value < 70 and rsi_value > 25,
            macd_value < macd_signal * 0.95,
            
            # Mean reversion from high
            current_price >= bb_middle * 0.97,
            current_price < bb_upper * 0.98,
            
            # Volume confirmation
            current_volume > avg_volume * 0.8,
            
            # Time filter
            current_time.hour >= 10 and current_time.hour < 15,
            
            # Not in dividend boost period
            not self.dividend_boost_active
        ]
        
        # Execute trades (high threshold for REIT)
        if sum(long_conditions) >= 11:  # Very high conviction for REIT
            self.EnterLongPosition(current_price, potential_shares)
        elif sum(short_conditions) >= 10:  # Very selective shorts for dividend REIT
            self.EnterShortPosition(current_price, potential_shares)
    
    def EnterLongPosition(self, entry_price, shares):
        """Enter long position optimized for O"""
        if shares > 0:
            self.MarketOrder(self.o, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = shares * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            dividend_msg = " (MONTHLY DIVIDEND BOOST)" if self.dividend_boost_active else ""
            self.Log(f"LONG O: {shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%){dividend_msg}")
    
    def EnterShortPosition(self, entry_price, shares):
        """Enter short position (very conservative for monthly dividend REIT)"""
        # Significantly reduce short size for dividend REIT
        short_shares = -int(shares * 0.4)  # Only 40% of long position size
        
        if short_shares < 0:
            self.MarketOrder(self.o, short_shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = abs(short_shares) * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"SHORT O: {short_shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%)")
    
    def CheckExitConditions(self, current_price, current_time):
        """Exit conditions optimized for O REIT characteristics"""
        position = self.Portfolio[self.o]
        
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
        
        # Take profit (higher target for REIT)
        if pnl_pct >= self.take_profit_pct:
            should_exit = True
            exit_reason = "TAKE_PROFIT"
        
        # Stop loss (wider for REIT volatility)
        elif pnl_pct <= -self.stop_loss_pct:
            should_exit = True
            exit_reason = "STOP_LOSS"
        
        # Time-based exits after minimum hold
        elif minutes_held >= self.min_hold_minutes:
            
            # Trend reversal exit
            if position.IsLong and self.ema_fast.Current.Value < self.ema_slow.Current.Value * 0.997:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            elif position.IsShort and self.ema_fast.Current.Value > self.ema_slow.Current.Value * 1.003:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            
            # RSI extreme exit (wider ranges for REIT)
            elif position.IsLong and self.rsi.Current.Value > 80:
                should_exit = True
                exit_reason = "RSI_OVERBOUGHT"
            elif position.IsShort and self.rsi.Current.Value < 20:
                should_exit = True
                exit_reason = "RSI_OVERSOLD"
            
            # Interest rate environment change
            elif position.IsLong and self.interest_rate_environment == "UNFAVORABLE":
                if days_held >= 3:  # Give some time for reversal
                    should_exit = True
                    exit_reason = "INTEREST_RATE_RISK"
            
            # Mean reversion profit taking
            elif position.IsLong and current_price > self.bb.UpperBand.Current.Value:
                should_exit = True
                exit_reason = "MEAN_REVERSION_HIGH"
            elif position.IsShort and current_price < self.bb.LowerBand.Current.Value:
                should_exit = True
                exit_reason = "MEAN_REVERSION_LOW"
            
            # Maximum hold period
            elif days_held >= self.max_hold_days:
                should_exit = True
                exit_reason = "MAX_HOLD_PERIOD"
            
            # End of day exit
            elif current_time.hour >= 15 and current_time.minute >= 45:
                should_exit = True
                exit_reason = "END_OF_DAY"
        
        # Emergency protection for small account
        if pnl_pct <= -0.07:  # 7% emergency stop for REIT
            should_exit = True
            exit_reason = "EMERGENCY_STOP"
        
        # Monthly dividend protection for shorts
        if position.IsShort and self.dividend_boost_active:
            should_exit = True
            exit_reason = "MONTHLY_DIVIDEND_PROTECTION"
        
        # Execute exit
        if should_exit:
            self.Liquidate(self.o)
            profit = pnl_pct * 100
            trade_pnl = position.Quantity * (current_price - self.entry_price) if position.IsLong else position.Quantity * (self.entry_price - current_price)
            
            self.Log(f"EXIT O ({exit_reason}): P&L = {profit:.2f}% (${trade_pnl:.2f}) after {days_held:.1f} days")
            
            # Reset tracking variables
            self.entry_price = 0
            self.position_entry_time = None
    
    def AllIndicatorsReady(self):
        """Check if all indicators are ready"""
        indicators = [
            self.ema_fast, self.ema_slow, self.ema_trend,
            self.rsi, self.macd, self.bb, self.volume_sma,
            self.sma_200, self.atr, self.reit_momentum
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Log final performance for O small account"""
        final_value = self.Portfolio.TotalPortfolioValue
        initial_value = 6319
        total_return = (final_value - initial_value) / initial_value * 100
        
        self.Log(f"=== O (REALTY INCOME) REIT PERFORMANCE ===")
        self.Log(f"Initial Capital: ${initial_value:,.2f}")
        self.Log(f"Final Portfolio Value: ${final_value:,.2f}")
        self.Log(f"Total Return: {total_return:.2f}%")
        self.Log(f"Absolute Profit/Loss: ${final_value - initial_value:,.2f}")
        self.Log(f"Monthly Dividend Periods Captured: Various (O pays monthly)")