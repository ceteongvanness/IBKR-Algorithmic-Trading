from AlgorithmImports import *
import numpy as np

class HighWinRateTSLAStockAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash - optimized for smaller account
        self.SetCash(6319)  # Your current capital
        
        # Add TSLA (Tesla Inc.) - High volatility growth stock
        self.tsla = self.AddEquity("TSLA", Resolution.Minute).Symbol
        
        # Set benchmark to TSLA
        self.SetBenchmark(self.tsla)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # Risk management parameters (optimized for high volatility small account)
        self.max_position_size = 0.70      # 70% max position (conservative for TSLA volatility)
        self.stop_loss_pct = 0.06          # 6% stop loss (wider for TSLA's volatility)
        self.take_profit_pct = 0.12        # 12% take profit (higher reward for risk taken)
        
        # Small account optimizations for high volatility stock
        self.min_trade_value = 300         # Lower minimum for expensive stock
        self.max_trades_per_day = 1        # Very conservative limit for TSLA
        self.daily_trade_count = 0
        
        # Volatility and momentum tracking
        self.volatility_regime = "NORMAL"
        self.momentum_strength = "NEUTRAL"
        self.earnings_proximity = "CLEAR"
        
        # Trade management
        self.entry_price = 0
        self.position_entry_time = None
        self.min_hold_minutes = 30         # Shorter holds for high volatility
        self.max_hold_days = 5             # Shorter maximum for momentum stock
        
        # Market regime detection
        self.market_regime = "NEUTRAL"
        self.tech_sector_strength = "NEUTRAL"
        
        # Special TSLA factors
        self.musk_twitter_factor = "NEUTRAL"  # Simplified social sentiment proxy
        self.ev_sector_momentum = "NEUTRAL"
        
        # Schedule functions
        self.Schedule.On(self.DateRules.EveryDay(self.tsla), 
                        self.TimeRules.AfterMarketOpen(self.tsla, 30), 
                        self.CheckMarketRegime)
        
        self.Schedule.On(self.DateRules.EveryDay(self.tsla), 
                        self.TimeRules.AfterMarketOpen(self.tsla, 5), 
                        self.ResetDailyCounters)
        
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday), 
                        self.TimeRules.AfterMarketOpen(self.tsla, 60), 
                        self.CheckEarningsProximity)
        
        # Warm up period
        self.SetWarmUp(100)
        
    def Setup_Indicators(self):
        # Trend indicators (optimized for high volatility stock)
        self.ema_fast = self.EMA(self.tsla, 5, Resolution.Minute)     # Very fast for TSLA
        self.ema_slow = self.EMA(self.tsla, 15, Resolution.Minute)    # Quick reaction
        self.ema_trend = self.EMA(self.tsla, 30, Resolution.Minute)   # Short-term trend
        
        # Daily trend for stability
        self.daily_ema = self.EMA(self.tsla, 20, Resolution.Daily)
        self.daily_trend = self.EMA(self.tsla, 50, Resolution.Daily)
        
        # RSI for momentum (shorter period for fast-moving stock)
        self.rsi = self.RSI(self.tsla, 10, Resolution.Minute)
        
        # MACD for trend confirmation (faster settings)
        self.macd = self.MACD(self.tsla, 8, 17, 6, Resolution.Minute)
        
        # Bollinger Bands for volatility (wider for TSLA)
        self.bb = self.BB(self.tsla, 15, 3, Resolution.Minute)  # Wider bands
        
        # Volume indicators (critical for TSLA)
        self.volume_sma = self.SMA(self.tsla, 15, Resolution.Minute, Field.Volume)
        self.volume_spike = self.SMA(self.tsla, 5, Resolution.Minute, Field.Volume)
        
        # Volatility indicators
        self.atr = self.ATR(self.tsla, 10, Resolution.Minute)
        self.volatility_measure = RollingWindow[float](30)
        
        # Momentum indicators
        self.momentum_roc = self.ROC(self.tsla, 10, Resolution.Minute)  # Rate of change
        
        # Tech sector proxy (using TSLA's own weekly momentum)
        self.tech_momentum = self.RSI(self.tsla, 14, Resolution.Daily)
        
    def ResetDailyCounters(self):
        """Reset daily trade counter"""
        self.daily_trade_count = 0
        
    def CheckEarningsProximity(self):
        """Check if approaching TSLA earnings (quarterly)"""
        current_month = self.Time.month
        current_day = self.Time.day
        
        # TSLA typical earnings months: January, April, July, October
        earnings_months = [1, 4, 7, 10]
        
        if current_month in earnings_months:
            # Earnings blackout period: 1 week before and after mid-month
            if 15 <= current_day <= 25:
                self.earnings_proximity = "NEAR"
                self.Log(f"TSLA earnings proximity - reducing activity")
            else:
                self.earnings_proximity = "CLEAR"
        else:
            self.earnings_proximity = "CLEAR"
            
    def CheckMarketRegime(self):
        """Determine market regime for TSLA (high volatility factors)"""
        if not self.daily_trend.IsReady:
            return
            
        current_price = self.Securities[self.tsla].Price
        daily_ema_value = self.daily_ema.Current.Value
        daily_trend_value = self.daily_trend.Current.Value
        
        # Update volatility measure
        if self.atr.IsReady:
            atr_value = self.atr.Current.Value
            volatility_pct = (atr_value / current_price) * 100
            self.volatility_measure.Add(volatility_pct)
        
        # Volatility regime detection
        if len(self.volatility_measure) >= 20:
            recent_vol = np.mean([x for x in self.volatility_measure[:10]])
            if recent_vol > 8:  # High volatility threshold for TSLA
                self.volatility_regime = "HIGH"
            elif recent_vol < 4:  # Low volatility for TSLA
                self.volatility_regime = "LOW"
            else:
                self.volatility_regime = "NORMAL"
        
        # Market regime for growth stock
        bullish_signals = 0
        bearish_signals = 0
        
        # Daily trend alignment
        if current_price > daily_ema_value * 1.02:
            bullish_signals += 3
        elif current_price < daily_ema_value * 0.98:
            bearish_signals += 3
            
        # Longer-term trend
        if current_price > daily_trend_value:
            bullish_signals += 2
        elif current_price < daily_trend_value:
            bearish_signals += 2
            
        # Tech sector momentum
        if self.tech_momentum.IsReady:
            tech_rsi = self.tech_momentum.Current.Value
            if tech_rsi > 60:
                bullish_signals += 2
                self.tech_sector_strength = "STRONG"
            elif tech_rsi < 40:
                bearish_signals += 2
                self.tech_sector_strength = "WEAK"
            else:
                self.tech_sector_strength = "NEUTRAL"
        
        # Momentum strength
        if self.momentum_roc.IsReady:
            roc_value = self.momentum_roc.Current.Value
            if roc_value > 2:  # Strong positive momentum
                bullish_signals += 1
                self.momentum_strength = "STRONG"
            elif roc_value < -2:  # Strong negative momentum
                bearish_signals += 1
                self.momentum_strength = "WEAK"
            else:
                self.momentum_strength = "NEUTRAL"
        
        # Set market regime
        if bullish_signals >= 4 and bullish_signals > bearish_signals:
            self.market_regime = "BULLISH"
        elif bearish_signals >= 4 and bearish_signals > bullish_signals:
            self.market_regime = "BEARISH"
        else:
            self.market_regime = "NEUTRAL"
    
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        if not self.AllIndicatorsReady():
            return
            
        if not data.ContainsKey(self.tsla):
            return
            
        current_price = data[self.tsla].Close
        current_time = self.Time
        
        # Check for exit conditions first
        if self.Portfolio[self.tsla].Invested:
            self.CheckExitConditions(current_price, current_time)
        else:
            # Look for entry opportunities (very selective for TSLA)
            if self.daily_trade_count < self.max_trades_per_day:
                self.CheckEntryConditions(current_price, current_time, data)
    
    def CheckEntryConditions(self, current_price, current_time, data):
        """Entry conditions optimized for TSLA high volatility trading"""
        
        # Skip trading near earnings
        if self.earnings_proximity == "NEAR":
            return
        
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
        
        # Volume analysis (critical for TSLA)
        current_volume = data[self.tsla].Volume
        avg_volume = self.volume_sma.Current.Value
        recent_volume = self.volume_spike.Current.Value
        volume_spike = current_volume > avg_volume * 1.5  # Strong volume requirement
        volume_surge = recent_volume > avg_volume * 1.3   # Recent volume increase
        
        # Calculate potential trade size (smaller for TSLA due to price and volatility)
        available_capital = self.Portfolio.Cash
        max_trade_value = available_capital * self.max_position_size
        potential_shares = int(max_trade_value / current_price)
        trade_value = potential_shares * current_price
        
        # Skip if trade too small or too risky
        if trade_value < self.min_trade_value or potential_shares == 0:
            return
        
        # TSLA Long entry conditions (high conviction momentum)
        long_conditions = [
            # Strong momentum alignment
            ema_fast > ema_slow * 1.005,     # Clear short-term uptrend
            current_price > ema_trend * 1.01, # Above trend line
            current_price > self.daily_ema.Current.Value * 1.01,  # Daily uptrend
            
            # Market regime strongly bullish
            self.market_regime == "BULLISH",
            
            # Tech sector strength
            self.tech_sector_strength in ["STRONG", "NEUTRAL"],
            
            # Momentum confirmation
            self.momentum_strength in ["STRONG", "NEUTRAL"],
            
            # RSI momentum (not overbought)
            rsi_value > 50 and rsi_value < 80,
            
            # MACD strong signal
            macd_value > macd_signal * 1.02,
            
            # Breakout or pullback setup
            (current_price > bb_upper * 0.98) or (current_price > bb_lower * 1.05 and current_price < bb_middle * 1.02),
            
            # Volume confirmation (critical for TSLA)
            volume_spike or volume_surge,
            
            # Volatility regime suitable
            self.volatility_regime in ["NORMAL", "HIGH"],
            
            # Time filter (avoid first hour due to volatility)
            current_time.hour >= 11 and current_time.hour < 15,
            
            # Trade size manageable
            trade_value >= self.min_trade_value,
            
            # Not near earnings
            self.earnings_proximity == "CLEAR"
        ]
        
        # Short entry conditions (very selective for TSLA)
        short_conditions = [
            # Strong bearish momentum
            ema_fast < ema_slow * 0.995,
            current_price < ema_trend * 0.99,
            current_price < self.daily_ema.Current.Value * 0.99,
            
            # Market regime bearish
            self.market_regime == "BEARISH",
            
            # Tech sector weakness
            self.tech_sector_strength == "WEAK",
            
            # Momentum weakness
            self.momentum_strength == "WEAK",
            
            # RSI showing weakness
            rsi_value < 50 and rsi_value > 20,
            
            # MACD bearish
            macd_value < macd_signal * 0.98,
            
            # Breakdown setup
            current_price < bb_lower * 1.02 or (current_price < bb_upper * 0.95 and current_price > bb_middle * 0.98),
            
            # Volume confirmation
            volume_spike,
            
            # High volatility for breakdown
            self.volatility_regime == "HIGH",
            
            # Time filter
            current_time.hour >= 11 and current_time.hour < 15,
            
            # Not near earnings
            self.earnings_proximity == "CLEAR"
        ]
        
        # Execute trades (very high threshold for TSLA)
        if sum(long_conditions) >= 12:  # Extremely high conviction for TSLA long
            self.EnterLongPosition(current_price, potential_shares)
        elif sum(short_conditions) >= 11:  # High conviction for TSLA short
            self.EnterShortPosition(current_price, potential_shares)
    
    def EnterLongPosition(self, entry_price, shares):
        """Enter long position optimized for TSLA"""
        if shares > 0:
            self.MarketOrder(self.tsla, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = shares * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            vol_msg = f" (VOL: {self.volatility_regime})" if self.volatility_regime != "NORMAL" else ""
            self.Log(f"LONG TSLA: {shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%){vol_msg}")
    
    def EnterShortPosition(self, entry_price, shares):
        """Enter short position (very conservative for TSLA volatility)"""
        # Reduce short size significantly for high volatility stock
        short_shares = -int(shares * 0.6)  # 60% of long position size due to unlimited risk
        
        if short_shares < 0:
            self.MarketOrder(self.tsla, short_shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = abs(short_shares) * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"SHORT TSLA: {short_shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%)")
    
    def CheckExitConditions(self, current_price, current_time):
        """Exit conditions optimized for TSLA's high volatility"""
        position = self.Portfolio[self.tsla]
        
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
        
        # Take profit (higher target for TSLA volatility)
        if pnl_pct >= self.take_profit_pct:
            should_exit = True
            exit_reason = "TAKE_PROFIT"
        
        # Stop loss (wider for TSLA volatility)
        elif pnl_pct <= -self.stop_loss_pct:
            should_exit = True
            exit_reason = "STOP_LOSS"
        
        # Quick profit taking for high volatility
        elif pnl_pct >= 0.08 and minutes_held >= 30:  # 8% quick profit
            should_exit = True
            exit_reason = "QUICK_PROFIT"
        
        # Time-based exits after minimum hold
        elif minutes_held >= self.min_hold_minutes:
            
            # Fast trend reversal exit
            if position.IsLong and self.ema_fast.Current.Value < self.ema_slow.Current.Value:
                should_exit = True
                exit_reason = "FAST_TREND_REVERSAL"
            elif position.IsShort and self.ema_fast.Current.Value > self.ema_slow.Current.Value:
                should_exit = True
                exit_reason = "FAST_TREND_REVERSAL"
            
            # RSI extreme exit (tighter for TSLA)
            elif position.IsLong and self.rsi.Current.Value > 85:
                should_exit = True
                exit_reason = "RSI_EXTREME_HIGH"
            elif position.IsShort and self.rsi.Current.Value < 15:
                should_exit = True
                exit_reason = "RSI_EXTREME_LOW"
            
            # Momentum reversal
            elif position.IsLong and self.momentum_strength == "WEAK":
                should_exit = True
                exit_reason = "MOMENTUM_REVERSAL"
            elif position.IsShort and self.momentum_strength == "STRONG":
                should_exit = True
                exit_reason = "MOMENTUM_REVERSAL"
            
            # Volatility spike exit (protect profits)
            elif self.volatility_regime == "HIGH" and pnl_pct > 0.03:  # 3% profit in high vol
                should_exit = True
                exit_reason = "VOLATILITY_PROTECTION"
            
            # Maximum hold period (shorter for TSLA)
            elif days_held >= self.max_hold_days:
                should_exit = True
                exit_reason = "MAX_HOLD_PERIOD"
            
            # End of day exit (critical for TSLA)
            elif current_time.hour >= 15 and current_time.minute >= 30:
                should_exit = True
                exit_reason = "END_OF_DAY"
        
        # Emergency protection for small account with volatile stock
        if pnl_pct <= -0.10:  # 10% emergency stop for TSLA
            should_exit = True
            exit_reason = "EMERGENCY_STOP"
        
        # Earnings proximity protection
        if self.earnings_proximity == "NEAR":
            should_exit = True
            exit_reason = "EARNINGS_PROTECTION"
        
        # Execute exit
        if should_exit:
            self.Liquidate(self.tsla)
            profit = pnl_pct * 100
            trade_pnl = position.Quantity * (current_price - self.entry_price) if position.IsLong else position.Quantity * (self.entry_price - current_price)
            
            self.Log(f"EXIT TSLA ({exit_reason}): P&L = {profit:.2f}% (${trade_pnl:.2f}) after {minutes_held:.0f} min")
            
            # Reset tracking variables
            self.entry_price = 0
            self.position_entry_time = None
    
    def AllIndicatorsReady(self):
        """Check if all indicators are ready"""
        indicators = [
            self.ema_fast, self.ema_slow, self.ema_trend,
            self.rsi, self.macd, self.bb, self.volume_sma,
            self.daily_ema, self.daily_trend, self.atr,
            self.momentum_roc, self.tech_momentum
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Log final performance for TSLA small account"""
        final_value = self.Portfolio.TotalPortfolioValue
        initial_value = 6319
        total_return = (final_value - initial_value) / initial_value * 100
        
        self.Log(f"=== TSLA HIGH VOLATILITY PERFORMANCE ===")
        self.Log(f"Initial Capital: ${initial_value:,.2f}")
        self.Log(f"Final Portfolio Value: ${final_value:,.2f}")
        self.Log(f"Total Return: {total_return:.2f}%")
        self.Log(f"Absolute Profit/Loss: ${final_value - initial_value:,.2f}")
        self.Log(f"High Volatility Strategy - Risk/Reward Optimized")