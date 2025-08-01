from AlgorithmImports import *
import numpy as np

class HighWinRateMSFTStockAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash - optimized for smaller account
        self.SetCash(6319)  # Your current capital
        
        # Add MSFT (Microsoft Corporation) - Stable tech giant
        self.msft = self.AddEquity("MSFT", Resolution.Minute).Symbol
        
        # Set benchmark to MSFT
        self.SetBenchmark(self.msft)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # Risk management parameters (optimized for blue-chip tech small account)
        self.max_position_size = 0.85      # 85% max position (high confidence in MSFT)
        self.stop_loss_pct = 0.035         # 3.5% stop loss (moderate for tech stock)
        self.take_profit_pct = 0.055       # 5.5% take profit (achievable for MSFT)
        
        # Small account optimizations for blue-chip tech
        self.min_trade_value = 400         # Minimum $400 per trade
        self.max_trades_per_day = 2        # Conservative limit for quality stock
        self.daily_trade_count = 0
        
        # Tech-specific factors
        self.earnings_proximity = "CLEAR"
        self.cloud_sector_strength = "NEUTRAL"
        self.enterprise_momentum = "NEUTRAL"
        self.dividend_awareness = True     # MSFT pays quarterly dividends
        
        # Trade management
        self.entry_price = 0
        self.position_entry_time = None
        self.min_hold_minutes = 60         # Moderate holds for blue-chip
        self.max_hold_days = 12            # Medium-term positions
        
        # Market regime detection
        self.market_regime = "NEUTRAL"
        self.tech_sector_strength = "NEUTRAL"
        
        # Schedule functions
        self.Schedule.On(self.DateRules.EveryDay(self.msft), 
                        self.TimeRules.AfterMarketOpen(self.msft, 30), 
                        self.CheckMarketRegime)
        
        self.Schedule.On(self.DateRules.EveryDay(self.msft), 
                        self.TimeRules.AfterMarketOpen(self.msft, 5), 
                        self.ResetDailyCounters)
        
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday), 
                        self.TimeRules.AfterMarketOpen(self.msft, 60), 
                        self.CheckEarningsAndEvents)
        
        # Warm up period
        self.SetWarmUp(120)
        
    def Setup_Indicators(self):
        # Trend indicators (optimized for blue-chip tech characteristics)
        self.ema_fast = self.EMA(self.msft, 8, Resolution.Daily)     # Fast tech trend
        self.ema_slow = self.EMA(self.msft, 21, Resolution.Daily)    # Medium trend
        self.ema_trend = self.EMA(self.msft, 50, Resolution.Daily)   # Long term trend
        
        # Intraday trend for timing
        self.intraday_ema = self.EMA(self.msft, 20, Resolution.Minute)
        
        # Higher timeframe for stability
        self.sma_200 = self.SMA(self.msft, 200, Resolution.Daily)    # Long-term health
        
        # RSI for momentum (moderate period for blue-chip)
        self.rsi = self.RSI(self.msft, 14, Resolution.Daily)
        
        # MACD for trend confirmation
        self.macd = self.MACD(self.msft, 12, 26, 9, Resolution.Daily)
        
        # Bollinger Bands for volatility and mean reversion
        self.bb = self.BB(self.msft, 20, 2, Resolution.Daily)
        
        # Volume indicators (important for institutional stock)
        self.volume_sma = self.SMA(self.msft, 20, Resolution.Daily, Field.Volume)
        self.volume_surge = self.SMA(self.msft, 5, Resolution.Daily, Field.Volume)
        
        # ATR for volatility measurement
        self.atr = self.ATR(self.msft, 14, Resolution.Daily)
        
        # Tech sector momentum (using QQQ as proxy)
        self.tech_momentum = self.RSI(self.msft, 21, Resolution.Weekly)
        
        # Cloud/Enterprise strength proxy (MSFT's own momentum)
        self.enterprise_rsi = self.RSI(self.msft, 30, Resolution.Daily)
        
    def ResetDailyCounters(self):
        """Reset daily trade counter"""
        self.daily_trade_count = 0
        
    def CheckEarningsAndEvents(self):
        """Check for MSFT earnings and major tech events"""
        current_month = self.Time.month
        current_day = self.Time.day
        
        # MSFT typical earnings months: January, April, July, October
        earnings_months = [1, 4, 7, 10]
        
        if current_month in earnings_months:
            # Earnings consideration period
            if 15 <= current_day <= 30:
                self.earnings_proximity = "NEAR"
                self.Log(f"MSFT earnings proximity - adjusting strategy")
            else:
                self.earnings_proximity = "CLEAR"
        else:
            self.earnings_proximity = "CLEAR"
            
    def CheckMarketRegime(self):
        """Determine market regime for MSFT (blue-chip tech factors)"""
        if not self.sma_200.IsReady:
            return
            
        current_price = self.Securities[self.msft].Price
        sma_200_value = self.sma_200.Current.Value
        ema_50_value = self.ema_trend.Current.Value
        
        # Blue-chip tech regime detection
        bullish_signals = 0
        bearish_signals = 0
        
        # Long-term technology leadership (critical for MSFT)
        if current_price > sma_200_value * 1.02:
            bullish_signals += 3
        elif current_price < sma_200_value * 0.98:
            bearish_signals += 3
            
        # Medium-term trend
        if current_price > ema_50_value * 1.01:
            bullish_signals += 2
        elif current_price < ema_50_value * 0.99:
            bearish_signals += 2
            
        # Tech sector momentum
        if self.tech_momentum.IsReady:
            tech_rsi = self.tech_momentum.Current.Value
            if tech_rsi > 55:
                bullish_signals += 2
                self.tech_sector_strength = "STRONG"
            elif tech_rsi < 45:
                bearish_signals += 2
                self.tech_sector_strength = "WEAK"
            else:
                self.tech_sector_strength = "NEUTRAL"
        
        # Cloud/Enterprise sector strength
        if self.enterprise_rsi.IsReady:
            enterprise_rsi = self.enterprise_rsi.Current.Value
            if enterprise_rsi > 60:
                bullish_signals += 1
                self.cloud_sector_strength = "STRONG"
                self.enterprise_momentum = "STRONG"
            elif enterprise_rsi < 40:
                bearish_signals += 1
                self.cloud_sector_strength = "WEAK"
                self.enterprise_momentum = "WEAK"
            else:
                self.cloud_sector_strength = "NEUTRAL"
                self.enterprise_momentum = "NEUTRAL"
        
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
            
        if not data.ContainsKey(self.msft):
            return
            
        current_price = data[self.msft].Close
        current_time = self.Time
        
        # Check for exit conditions first
        if self.Portfolio[self.msft].Invested:
            self.CheckExitConditions(current_price, current_time)
        else:
            # Look for entry opportunities
            if self.daily_trade_count < self.max_trades_per_day:
                self.CheckEntryConditions(current_price, current_time, data)
    
    def CheckEntryConditions(self, current_price, current_time, data):
        """Entry conditions optimized for MSFT blue-chip tech trading"""
        
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
        intraday_ema = self.intraday_ema.Current.Value
        
        # Volume analysis (institutional participation important)
        current_volume = data[self.msft].Volume
        avg_volume = self.volume_sma.Current.Value
        recent_volume = self.volume_surge.Current.Value
        volume_confirmation = current_volume > avg_volume * 0.8
        volume_surge = recent_volume > avg_volume * 1.2
        
        # Calculate potential trade size
        available_capital = self.Portfolio.Cash
        max_trade_value = available_capital * self.max_position_size
        potential_shares = int(max_trade_value / current_price)
        trade_value = potential_shares * current_price
        
        # Skip if trade too small
        if trade_value < self.min_trade_value:
            return
        
        # MSFT Long entry conditions (blue-chip tech approach)
        long_conditions = [
            # Long-term technology leadership
            current_price > sma_200 * 0.99,  # Near or above long-term trend
            
            # Trend alignment
            ema_fast > ema_slow * 1.002,     # Uptrend developing
            current_price > ema_trend * 0.995, # Above medium-term trend
            current_price > intraday_ema,    # Intraday momentum
            
            # Market regime favorable for tech
            self.market_regime in ["BULLISH", "NEUTRAL"],
            
            # Tech sector strength
            self.tech_sector_strength in ["STRONG", "NEUTRAL"],
            
            # Cloud/Enterprise momentum
            self.enterprise_momentum in ["STRONG", "NEUTRAL"],
            
            # Conservative momentum (blue-chip approach)
            rsi_value > 40 and rsi_value < 75,
            
            # MACD confirmation
            macd_value > macd_signal * 0.98,
            
            # Mean reversion or breakout setup
            (current_price <= bb_middle * 1.02 and current_price > bb_lower * 1.03) or 
            (current_price > bb_upper * 0.98),  # Breakout setup
            
            # Volume confirmation (institutional interest)
            volume_confirmation,
            
            # Time filter (avoid first/last hour for blue-chip)
            current_time.hour >= 10 and current_time.hour < 15,
            
            # Trade size validation
            trade_value >= self.min_trade_value,
            
            # Earnings timing (less restrictive for blue-chip)
            self.earnings_proximity in ["CLEAR", "NEAR"]  # Can trade near earnings
        ]
        
        # Short entry conditions (conservative for blue-chip)
        short_conditions = [
            # Significant weakness in tech leadership
            current_price < sma_200 * 0.97,
            
            # Clear downtrend
            ema_fast < ema_slow * 0.998,
            current_price < ema_trend * 0.99,
            current_price < intraday_ema * 0.998,
            
            # Market regime bearish
            self.market_regime == "BEARISH",
            
            # Tech sector weakness
            self.tech_sector_strength == "WEAK",
            
            # Enterprise momentum weak
            self.enterprise_momentum == "WEAK",
            
            # Momentum confirmation
            rsi_value < 65 and rsi_value > 25,
            macd_value < macd_signal,
            
            # Mean reversion from high
            current_price >= bb_middle * 0.98,
            current_price < bb_upper * 0.97,
            
            # Volume confirmation
            volume_surge or current_volume > avg_volume * 1.0,
            
            # Time filter
            current_time.hour >= 10 and current_time.hour < 15,
            
            # Not near earnings (conservative for shorts)
            self.earnings_proximity == "CLEAR"
        ]
        
        # Execute trades (high threshold for blue-chip)
        if sum(long_conditions) >= 11:  # High conviction for MSFT
            self.EnterLongPosition(current_price, potential_shares)
        elif sum(short_conditions) >= 10:  # Conservative shorts for blue-chip
            self.EnterShortPosition(current_price, potential_shares)
    
    def EnterLongPosition(self, entry_price, shares):
        """Enter long position optimized for MSFT"""
        if shares > 0:
            self.MarketOrder(self.msft, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = shares * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            sector_msg = f" (TECH: {self.tech_sector_strength})" if self.tech_sector_strength != "NEUTRAL" else ""
            self.Log(f"LONG MSFT: {shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%){sector_msg}")
    
    def EnterShortPosition(self, entry_price, shares):
        """Enter short position (conservative for blue-chip)"""
        # Conservative short sizing for blue-chip tech
        short_shares = -int(shares * 0.7)  # 70% of long position size
        
        if short_shares < 0:
            self.MarketOrder(self.msft, short_shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = abs(short_shares) * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"SHORT MSFT: {short_shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%)")
    
    def CheckExitConditions(self, current_price, current_time):
        """Exit conditions optimized for MSFT blue-chip characteristics"""
        position = self.Portfolio[self.msft]
        
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
        
        # Take profit (moderate target for blue-chip)
        if pnl_pct >= self.take_profit_pct:
            should_exit = True
            exit_reason = "TAKE_PROFIT"
        
        # Stop loss (moderate for blue-chip tech)
        elif pnl_pct <= -self.stop_loss_pct:
            should_exit = True
            exit_reason = "STOP_LOSS"
        
        # Quick profit taking for momentum moves
        elif pnl_pct >= 0.04 and minutes_held >= 120:  # 4% after 2 hours
            should_exit = True
            exit_reason = "QUICK_PROFIT"
        
        # Time-based exits after minimum hold
        elif minutes_held >= self.min_hold_minutes:
            
            # Trend reversal exit
            if position.IsLong and self.ema_fast.Current.Value < self.ema_slow.Current.Value * 0.999:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            elif position.IsShort and self.ema_fast.Current.Value > self.ema_slow.Current.Value * 1.001:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            
            # RSI extreme exit
            elif position.IsLong and self.rsi.Current.Value > 80:
                should_exit = True
                exit_reason = "RSI_OVERBOUGHT"
            elif position.IsShort and self.rsi.Current.Value < 20:
                should_exit = True
                exit_reason = "RSI_OVERSOLD"
            
            # Tech sector momentum reversal
            elif position.IsLong and self.tech_sector_strength == "WEAK":
                if days_held >= 2:  # Give some time for sector recovery
                    should_exit = True
                    exit_reason = "TECH_SECTOR_WEAKNESS"
            elif position.IsShort and self.tech_sector_strength == "STRONG":
                should_exit = True
                exit_reason = "TECH_SECTOR_STRENGTH"
            
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
        if pnl_pct <= -0.06:  # 6% emergency stop
            should_exit = True
            exit_reason = "EMERGENCY_STOP"
        
        # Execute exit
        if should_exit:
            self.Liquidate(self.msft)
            profit = pnl_pct * 100
            trade_pnl = position.Quantity * (current_price - self.entry_price) if position.IsLong else position.Quantity * (self.entry_price - current_price)
            
            self.Log(f"EXIT MSFT ({exit_reason}): P&L = {profit:.2f}% (${trade_pnl:.2f}) after {days_held:.1f} days")
            
            # Reset tracking variables
            self.entry_price = 0
            self.position_entry_time = None
    
    def AllIndicatorsReady(self):
        """Check if all indicators are ready"""
        indicators = [
            self.ema_fast, self.ema_slow, self.ema_trend,
            self.rsi, self.macd, self.bb, self.volume_sma,
            self.sma_200, self.atr, self.tech_momentum,
            self.intraday_ema, self.enterprise_rsi
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Log final performance for MSFT small account"""
        final_value = self.Portfolio.TotalPortfolioValue
        initial_value = 6319
        total_return = (final_value - initial_value) / initial_value * 100
        
        self.Log(f"=== MSFT BLUE-CHIP TECH PERFORMANCE ===")
        self.Log(f"Initial Capital: ${initial_value:,.2f}")
        self.Log(f"Final Portfolio Value: ${final_value:,.2f}")
        self.Log(f"Total Return: {total_return:.2f}%")
        self.Log(f"Absolute Profit/Loss: ${final_value - initial_value:,.2f}")
        self.Log(f"Blue-chip Technology Strategy - Balanced Growth")