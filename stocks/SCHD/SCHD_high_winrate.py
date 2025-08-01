from AlgorithmImports import *
import numpy as np

class HighWinRateSCHDStockAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash - optimized for smaller account
        self.SetCash(6319)  # Your current capital
        
        # Add SCHD (Schwab US Dividend Equity ETF)
        self.schd = self.AddEquity("SCHD", Resolution.Minute).Symbol
        
        # Set benchmark to SCHD
        self.SetBenchmark(self.schd)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # Risk management parameters (optimized for dividend ETF small account)
        self.max_position_size = 0.85       # 85% max position (conservative for dividend ETF)
        self.stop_loss_pct = 0.03          # 3% stop loss (wider for dividend-focused ETF)
        self.take_profit_pct = 0.05        # 5% take profit (higher target for stable ETF)
        
        # Small account optimizations for dividend ETF
        self.min_trade_value = 400         # Minimum $400 per trade
        self.max_trades_per_day = 2        # Conservative limit for dividend strategy
        self.daily_trade_count = 0
        
        # Dividend-aware settings
        self.dividend_schedule = self.InitializeDividendSchedule()
        self.dividend_boost_period = False
        
        # Trade management
        self.entry_price = 0
        self.position_entry_time = None
        self.min_hold_minutes = 60         # Longer holds for dividend ETF
        self.max_hold_days = 14            # Maximum hold for mean reversion
        
        # Market regime detection
        self.market_regime = "NEUTRAL"
        self.dividend_sector_strength = "NEUTRAL"
        
        # Schedule functions
        self.Schedule.On(self.DateRules.EveryDay(self.schd), 
                        self.TimeRules.AfterMarketOpen(self.schd, 30), 
                        self.CheckMarketRegime)
        
        self.Schedule.On(self.DateRules.EveryDay(self.schd), 
                        self.TimeRules.AfterMarketOpen(self.schd, 5), 
                        self.ResetDailyCounters)
        
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday), 
                        self.TimeRules.AfterMarketOpen(self.schd, 60), 
                        self.CheckDividendSchedule)
        
        # Warm up period
        self.SetWarmUp(100)
        
    def Setup_Indicators(self):
        # Trend indicators (optimized for dividend ETF characteristics)
        self.ema_fast = self.EMA(self.schd, 12, Resolution.Daily)    # Faster for dividend trends
        self.ema_slow = self.EMA(self.schd, 26, Resolution.Daily)    # Medium term
        self.ema_trend = self.EMA(self.schd, 50, Resolution.Daily)   # Long term dividend trend
        
        # Higher timeframe for stability
        self.sma_200 = self.SMA(self.schd, 200, Resolution.Daily)    # Long-term trend
        
        # RSI for momentum (longer period for stable ETF)
        self.rsi = self.RSI(self.schd, 21, Resolution.Daily)
        
        # MACD for trend confirmation
        self.macd = self.MACD(self.schd, 12, 26, 9, Resolution.Daily)
        
        # Bollinger Bands for volatility and mean reversion
        self.bb = self.BB(self.schd, 20, 2, Resolution.Daily)
        
        # Volume indicators
        self.volume_sma = self.SMA(self.schd, 20, Resolution.Daily, Field.Volume)
        
        # ATR for volatility measurement
        self.atr = self.ATR(self.schd, 14, Resolution.Daily)
        
        # Dividend yield proxy (price-based estimation)
        self.dividend_yield_proxy = RollingWindow[float](252)
        
    def InitializeDividendSchedule(self):
        """Initialize SCHD dividend schedule (quarterly)"""
        return {
            'frequency': 'quarterly',
            'typical_months': [3, 6, 9, 12],  # March, June, September, December
            'ex_dividend_week': 3,  # Typically third week of month
            'boost_period_days': 14  # Days before ex-dividend to increase activity
        }
        
    def ResetDailyCounters(self):
        """Reset daily trade counter"""
        self.daily_trade_count = 0
        
    def CheckDividendSchedule(self):
        """Check if we're approaching dividend period"""
        current_month = self.Time.month
        current_day = self.Time.day
        
        # Check if approaching dividend month
        if current_month in self.dividend_schedule['typical_months']:
            # Boost period: 2 weeks before typical ex-dividend
            if 10 <= current_day <= 25:
                self.dividend_boost_period = True
                self.Log(f"Entering dividend boost period for SCHD in month {current_month}")
            else:
                self.dividend_boost_period = False
        else:
            self.dividend_boost_period = False
            
    def CheckMarketRegime(self):
        """Determine market regime for SCHD (dividend-focused)"""
        if not self.sma_200.IsReady:
            return
            
        current_price = self.Securities[self.schd].Price
        sma_200_value = self.sma_200.Current.Value
        ema_50_value = self.ema_trend.Current.Value
        
        # Update dividend yield proxy
        if current_price > 0:
            self.dividend_yield_proxy.Add(1.0 / current_price)
        
        # Dividend ETF regime detection (more conservative)
        bullish_signals = 0
        bearish_signals = 0
        
        # Long-term trend (critical for dividend investing)
        if current_price > sma_200_value * 1.02:
            bullish_signals += 3
        elif current_price < sma_200_value * 0.98:
            bearish_signals += 3
            
        # Medium-term trend
        if current_price > ema_50_value:
            bullish_signals += 2
        elif current_price < ema_50_value:
            bearish_signals += 2
            
        # Dividend sector strength (using SCHD's own momentum)
        if self.rsi.IsReady:
            rsi_value = self.rsi.Current.Value
            if rsi_value > 55:
                bullish_signals += 1
                self.dividend_sector_strength = "STRONG"
            elif rsi_value < 45:
                bearish_signals += 1
                self.dividend_sector_strength = "WEAK"
            else:
                self.dividend_sector_strength = "NEUTRAL"
        
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
            
        if not data.ContainsKey(self.schd):
            return
            
        current_price = data[self.schd].Close
        current_time = self.Time
        
        # Check for exit conditions first
        if self.Portfolio[self.schd].Invested:
            self.CheckExitConditions(current_price, current_time)
        else:
            # Look for entry opportunities
            if self.daily_trade_count < self.max_trades_per_day:
                self.CheckEntryConditions(current_price, current_time, data)
    
    def CheckEntryConditions(self, current_price, current_time, data):
        """Entry conditions optimized for SCHD dividend ETF trading"""
        
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
        current_volume = data[self.schd].Volume
        avg_volume = self.volume_sma.Current.Value
        volume_adequate = current_volume > avg_volume * 0.7
        
        # Calculate potential trade size
        available_capital = self.Portfolio.Cash
        max_trade_value = available_capital * self.max_position_size
        potential_shares = int(max_trade_value / current_price)
        trade_value = potential_shares * current_price
        
        # Skip if trade too small
        if trade_value < self.min_trade_value:
            return
        
        # SCHD Long entry conditions (dividend-focused approach)
        long_conditions = [
            # Long-term dividend sustainability
            current_price > sma_200,
            
            # Medium-term trend alignment
            ema_fast > ema_slow,
            current_price > ema_trend,
            
            # Market regime favorable for dividend stocks
            self.market_regime in ["BULLISH", "NEUTRAL"],
            
            # Dividend sector strength
            self.dividend_sector_strength in ["STRONG", "NEUTRAL"],
            
            # Conservative momentum (not overbought)
            rsi_value > 35 and rsi_value < 70,
            
            # MACD trend confirmation
            macd_value > macd_signal * 0.95,
            
            # Mean reversion opportunity (buy dips in dividend ETF)
            current_price <= bb_middle * 1.02,
            current_price > bb_lower * 1.05,
            
            # Volume adequate for ETF
            volume_adequate,
            
            # Time filter (avoid first/last hour)
            current_time.hour >= 10 and current_time.hour < 15,
            
            # Trade size validation
            trade_value >= self.min_trade_value
        ]
        
        # Dividend boost condition
        if self.dividend_boost_period:
            long_conditions.append(True)  # Extra condition during dividend approach
        
        # Short entry conditions (conservative for dividend ETF)
        short_conditions = [
            # Significant weakness in dividend sector
            current_price < sma_200 * 0.97,
            
            # Clear downtrend
            ema_fast < ema_slow,
            current_price < ema_trend * 0.98,
            
            # Market regime clearly bearish
            self.market_regime == "BEARISH",
            
            # Dividend sector weakness
            self.dividend_sector_strength == "WEAK",
            
            # Momentum confirmation
            rsi_value < 65 and rsi_value > 30,
            macd_value < macd_signal,
            
            # Mean reversion from high
            current_price >= bb_middle * 0.98,
            current_price < bb_upper * 0.95,
            
            # Volume confirmation
            current_volume > avg_volume * 0.9,
            
            # Time filter
            current_time.hour >= 10 and current_time.hour < 15,
            
            # Not in dividend boost period
            not self.dividend_boost_period
        ]
        
        # Execute trades (higher threshold for dividend ETF)
        if sum(long_conditions) >= 10:  # High conviction for dividend ETF
            self.EnterLongPosition(current_price, potential_shares)
        elif sum(short_conditions) >= 9:  # Very selective shorts for dividend ETF
            self.EnterShortPosition(current_price, potential_shares)
    
    def EnterLongPosition(self, entry_price, shares):
        """Enter long position optimized for SCHD"""
        if shares > 0:
            self.MarketOrder(self.schd, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = shares * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            boost_msg = " (DIVIDEND BOOST)" if self.dividend_boost_period else ""
            self.Log(f"LONG SCHD: {shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%){boost_msg}")
    
    def EnterShortPosition(self, entry_price, shares):
        """Enter short position (very conservative for dividend ETF)"""
        # Reduce short size significantly for dividend ETF
        short_shares = -int(shares * 0.5)  # Only 50% of long position size
        
        if short_shares < 0:
            self.MarketOrder(self.schd, short_shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = abs(short_shares) * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"SHORT SCHD: {short_shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%)")
    
    def CheckExitConditions(self, current_price, current_time):
        """Exit conditions optimized for SCHD dividend ETF characteristics"""
        position = self.Portfolio[self.schd]
        
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
        
        # Take profit (higher target for dividend ETF)
        if pnl_pct >= self.take_profit_pct:
            should_exit = True
            exit_reason = "TAKE_PROFIT"
        
        # Stop loss (wider for dividend ETF)
        elif pnl_pct <= -self.stop_loss_pct:
            should_exit = True
            exit_reason = "STOP_LOSS"
        
        # Time-based exits after minimum hold
        elif minutes_held >= self.min_hold_minutes:
            
            # Trend reversal exit
            if position.IsLong and self.ema_fast.Current.Value < self.ema_slow.Current.Value * 0.998:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            elif position.IsShort and self.ema_fast.Current.Value > self.ema_slow.Current.Value * 1.002:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            
            # RSI extreme exit (wider ranges for dividend ETF)
            elif position.IsLong and self.rsi.Current.Value > 78:
                should_exit = True
                exit_reason = "RSI_OVERBOUGHT"
            elif position.IsShort and self.rsi.Current.Value < 22:
                should_exit = True
                exit_reason = "RSI_OVERSOLD"
            
            # Mean reversion profit taking
            elif position.IsLong and current_price > self.bb.UpperBand.Current.Value:
                should_exit = True
                exit_reason = "MEAN_REVERSION_HIGH"
            elif position.IsShort and current_price < self.bb.LowerBand.Current.Value:
                should_exit = True
                exit_reason = "MEAN_REVERSION_LOW"
            
            # Maximum hold period for mean reversion
            elif days_held >= self.max_hold_days:
                should_exit = True
                exit_reason = "MAX_HOLD_PERIOD"
            
            # End of day exit
            elif current_time.hour >= 15 and current_time.minute >= 45:
                should_exit = True
                exit_reason = "END_OF_DAY"
        
        # Emergency protection for small account
        if pnl_pct <= -0.06:  # 6% emergency stop for small account
            should_exit = True
            exit_reason = "EMERGENCY_STOP"
        
        # Dividend period protection for shorts
        if position.IsShort and self.dividend_boost_period:
            should_exit = True
            exit_reason = "DIVIDEND_PROTECTION"
        
        # Execute exit
        if should_exit:
            self.Liquidate(self.schd)
            profit = pnl_pct * 100
            trade_pnl = position.Quantity * (current_price - self.entry_price) if position.IsLong else position.Quantity * (self.entry_price - current_price)
            
            self.Log(f"EXIT SCHD ({exit_reason}): P&L = {profit:.2f}% (${trade_pnl:.2f}) after {days_held:.1f} days")
            
            # Reset tracking variables
            self.entry_price = 0
            self.position_entry_time = None
    
    def AllIndicatorsReady(self):
        """Check if all indicators are ready"""
        indicators = [
            self.ema_fast, self.ema_slow, self.ema_trend,
            self.rsi, self.macd, self.bb, self.volume_sma,
            self.sma_200, self.atr
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Log final performance for SCHD small account"""
        final_value = self.Portfolio.TotalPortfolioValue
        initial_value = 6319
        total_return = (final_value - initial_value) / initial_value * 100
        
        self.Log(f"=== SCHD DIVIDEND ETF PERFORMANCE ===")
        self.Log(f"Initial Capital: ${initial_value:,.2f}")
        self.Log(f"Final Portfolio Value: ${final_value:,.2f}")
        self.Log(f"Total Return: {total_return:.2f}%")
        self.Log(f"Absolute Profit/Loss: ${final_value - initial_value:,.2f}")
        
        # Calculate dividend capture efficiency
        if hasattr(self, 'dividend_periods_traded'):
            self.Log(f"Dividend Periods Traded: {getattr(self, 'dividend_periods_traded', 'N/A')}")