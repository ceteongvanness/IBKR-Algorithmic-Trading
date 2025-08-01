from AlgorithmImports import *
import numpy as np

class HighWinRateKOStockAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash - optimized for smaller account
        self.SetCash(6319)  # Your current capital
        
        # Add KO (Coca-Cola) with minute resolution
        self.ko = self.AddEquity("KO", Resolution.Minute).Symbol
        
        # Set benchmark to KO
        self.SetBenchmark(self.ko)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # Risk management parameters (optimized for small account)
        self.max_position_size = 0.80       # 80% max position (conservative for dividend stock)
        self.stop_loss_pct = 0.025           # 2.5% stop loss 
        self.take_profit_pct = 0.045         # 4.5% take profit (higher for KO's lower volatility)
        
        # Small account optimizations for KO
        self.min_trade_value = 300           # Minimum $300 per trade (KO lower price)
        self.max_trades_per_day = 2          # Conservative trade limit
        self.daily_trade_count = 0
        
        # Trade management
        self.entry_price = 0
        self.position_entry_time = None
        self.min_hold_minutes = 60       # Longer hold for less volatile stock
        self.max_hold_days = 10          # Maximum hold period for mean reversion
        
        # Market regime detection
        self.market_regime = "NEUTRAL"
        self.dividend_aware = True       # KO is dividend stock
        
        # Consumer staples specific factors
        self.sector_momentum = "NEUTRAL"
        
        # Schedule functions
        self.Schedule.On(self.DateRules.EveryDay(self.ko), 
                        self.TimeRules.AfterMarketOpen(self.ko, 30), 
                        self.CheckMarketRegime)
        
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday), 
                        self.TimeRules.AfterMarketOpen(self.ko, 60), 
                        self.WeeklyAnalysis)
        
        # Warm up period
        self.SetWarmUp(200)
        
    def Setup_Indicators(self):
        # Trend indicators (adjusted for KO's characteristics)
        self.ema_fast = self.EMA(self.ko, 8, Resolution.Daily)    # Faster for defensive stock
        self.ema_slow = self.EMA(self.ko, 21, Resolution.Daily)   # Medium term
        self.ema_trend = self.EMA(self.ko, 50, Resolution.Daily)  # Long term trend
        
        # RSI for momentum (longer period for smoother signals)
        self.rsi = self.RSI(self.ko, 21, Resolution.Daily)
        
        # MACD for trend confirmation
        self.macd = self.MACD(self.ko, 12, 26, 9, Resolution.Daily)
        
        # Bollinger Bands for volatility and mean reversion
        self.bb = self.BB(self.ko, 20, 2, Resolution.Daily)
        
        # Volume indicators
        self.volume_sma = self.SMA(self.ko, 20, Resolution.Daily, Field.Volume)
        self.volume_ratio = self.SMA(self.ko, 5, Resolution.Daily, Field.Volume)
        
        # Dividend-aware indicators
        self.price_sma_200 = self.SMA(self.ko, 200, Resolution.Daily)
        
        # Volatility indicators
        self.atr = self.ATR(self.ko, 14, Resolution.Daily)
        
        # Consumer staples sector proxy (using XLP if available)
        # For simplicity, we'll use KO's own momentum
        self.sector_rsi = self.RSI(self.ko, 14, Resolution.Weekly)
        
    def CheckMarketRegime(self):
        """Determine market regime for KO specifically"""
        if not self.price_sma_200.IsReady:
            return
            
        current_price = self.Securities[self.ko].Price
        sma_200 = self.price_sma_200.Current.Value
        ema_50 = self.ema_trend.Current.Value
        
        # KO-specific regime detection (conservative approach)
        if current_price > sma_200 * 1.05 and current_price > ema_50:
            self.market_regime = "BULLISH"
        elif current_price < sma_200 * 0.95 and current_price < ema_50:
            self.market_regime = "BEARISH"
        else:
            self.market_regime = "NEUTRAL"
    
    def WeeklyAnalysis(self):
        """Weekly analysis for consumer staples momentum"""
        if not self.sector_rsi.IsReady:
            return
            
        sector_rsi_value = self.sector_rsi.Current.Value
        
        if sector_rsi_value > 60:
            self.sector_momentum = "STRONG"
        elif sector_rsi_value < 40:
            self.sector_momentum = "WEAK"
        else:
            self.sector_momentum = "NEUTRAL"
    
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        if not self.AllIndicatorsReady():
            return
            
        if not data.ContainsKey(self.ko):
            return
            
        current_price = data[self.ko].Close
        current_time = self.Time
        
        # Check for exit conditions first
        if self.Portfolio[self.ko].Invested:
            self.CheckExitConditions(current_price, current_time)
        else:
            # Look for entry opportunities
            self.CheckEntryConditions(current_price, current_time, data)
    
    def CheckEntryConditions(self, current_price, current_time, data):
        """High probability entry conditions for KO"""
        
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
        sma_200 = self.price_sma_200.Current.Value
        
        # Volume analysis
        current_volume = data[self.ko].Volume
        avg_volume = self.volume_sma.Current.Value
        recent_volume = self.volume_ratio.Current.Value
        volume_spike = current_volume > avg_volume * 1.3
        
        # KO-specific conditions for long entries (dividend stock approach)
        long_conditions = [
            # Long-term uptrend (important for dividend stocks)
            current_price > sma_200,
            
            # Medium-term trend alignment
            ema_fast > ema_slow,
            current_price > ema_trend,
            
            # Market regime favorable
            self.market_regime in ["BULLISH", "NEUTRAL"],
            
            # Sector momentum
            self.sector_momentum in ["STRONG", "NEUTRAL"],
            
            # Mean reversion in uptrend (buy dips)
            current_price < bb_middle * 1.02,  # Near or below middle BB
            current_price > bb_lower * 1.03,   # But not at extreme lows
            
            # Conservative momentum (not overbought)
            rsi_value > 35 and rsi_value < 65,
            
            # MACD confirmation
            macd_value > macd_signal * 0.98,  # Slight momentum
            
            # Volume confirmation (less critical for KO)
            current_volume > avg_volume * 0.7,
            
            # Avoid earnings-related volatility periods
            self.TimeUntilEarnings() > 5 or self.TimeUntilEarnings() < -2
        ]
        
        # Short entry conditions (more conservative for dividend stock)
        short_conditions = [
            # Significant downtrend
            current_price < sma_200 * 0.98,
            
            # Short-term trend down
            ema_fast < ema_slow,
            current_price < ema_trend,
            
            # Market regime bearish
            self.market_regime == "BEARISH",
            
            # Sector weakness
            self.sector_momentum in ["WEAK", "NEUTRAL"],
            
            # Mean reversion in downtrend
            current_price > bb_middle * 0.98,
            current_price < bb_upper * 0.97,
            
            # Momentum confirmation
            rsi_value < 65 and rsi_value > 35,
            macd_value < macd_signal * 1.02,
            
            # Volume
            volume_spike or current_volume > avg_volume * 0.8,
            
            # Timing
            self.TimeUntilEarnings() > 5 or self.TimeUntilEarnings() < -2
        ]
        
        # Execute trades (require more conditions for KO's stability)
        if sum(long_conditions) >= 8:  # Higher threshold for conservative stock
            self.EnterLongPosition(current_price)
        elif sum(short_conditions) >= 7:  # Fewer short trades for dividend stock
            self.EnterShortPosition(current_price)
    
    def TimeUntilEarnings(self):
        """Estimate days until earnings (simplified)"""
        # KO typically reports quarterly
        # This is a simplified approach - in practice, use earnings calendar
        current_month = self.Time.month
        
        # Typical KO earnings months: February, April, July, October
        earnings_months = [2, 4, 7, 10]
        
        for month in earnings_months:
            if current_month <= month:
                # Rough estimate - typically mid-month
                days_diff = (month - current_month) * 30 + 15 - self.Time.day
                return days_diff
        
        # Next year's February
        return (14 - current_month) * 30 + 15 - self.Time.day
    
    def EnterLongPosition(self, entry_price):
        """Enter long position with KO-appropriate sizing"""
        # Position sizing based on ATR (more conservative for dividend stock)
        atr_value = self.atr.Current.Value
        risk_per_share = max(atr_value * 2.0, entry_price * self.stop_loss_pct)
        
        # Calculate position size (more conservative risk)
        portfolio_risk = self.Portfolio.TotalPortfolioValue * 0.015  # Risk 1.5% of portfolio
        shares = int(portfolio_risk / risk_per_share)
        
        # Limit position size
        max_shares = int(self.Portfolio.TotalPortfolioValue * self.max_position_size / entry_price)
        shares = min(shares, max_shares)
        
        if shares > 0:
            self.MarketOrder(self.ko, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.Log(f"LONG KO: {shares} shares at ${entry_price:.2f}")
    
    def EnterShortPosition(self, entry_price):
        """Enter short position (conservative for dividend stock)"""
        # More conservative sizing for shorting dividend stock
        atr_value = self.atr.Current.Value
        risk_per_share = max(atr_value * 2.0, entry_price * self.stop_loss_pct)
        
        # Calculate position size (smaller for short)
        portfolio_risk = self.Portfolio.TotalPortfolioValue * 0.01  # Risk only 1% for shorts
        shares = -int(portfolio_risk / risk_per_share)
        
        # Limit position size
        max_shares = -int(self.Portfolio.TotalPortfolioValue * 0.3 / entry_price)  # Max 30% for shorts
        shares = max(shares, max_shares)
        
        if shares < 0:
            self.MarketOrder(self.ko, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.Log(f"SHORT KO: {shares} shares at ${entry_price:.2f}")
    
    def CheckExitConditions(self, current_price, current_time):
        """Exit conditions optimized for KO's characteristics"""
        position = self.Portfolio[self.ko]
        
        if position.Quantity == 0:
            return
            
        # Calculate P&L
        if position.IsLong:
            pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:
            pnl_pct = (self.entry_price - current_price) / self.entry_price
        
        # Time-based metrics
        minutes_held = (current_time - self.position_entry_time).total_seconds() / 60
        days_held = minutes_held / (60 * 24)
        
        # Exit conditions
        should_exit = False
        exit_reason = ""
        
        # Take profit (higher target for less volatile stock)
        if pnl_pct >= self.take_profit_pct:
            should_exit = True
            exit_reason = "TAKE_PROFIT"
        
        # Stop loss
        elif pnl_pct <= -self.stop_loss_pct:
            should_exit = True
            exit_reason = "STOP_LOSS"
        
        # Time-based exits after minimum hold
        elif minutes_held >= self.min_hold_minutes:
            
            # Trend reversal exit
            if position.IsLong and self.ema_fast.Current.Value < self.ema_slow.Current.Value * 0.999:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            elif position.IsShort and self.ema_fast.Current.Value > self.ema_slow.Current.Value * 1.001:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            
            # RSI extreme exit (wider ranges for KO)
            elif position.IsLong and self.rsi.Current.Value > 75:
                should_exit = True
                exit_reason = "RSI_OVERBOUGHT"
            elif position.IsShort and self.rsi.Current.Value < 25:
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
            
            # End of day exit (less critical for KO but still important)
            elif current_time.hour >= 15 and current_time.minute >= 45:
                should_exit = True
                exit_reason = "END_OF_DAY"
        
        # Dividend-related exit (avoid holding short through ex-dividend)
        if position.IsShort and self.IsNearExDividend():
            should_exit = True
            exit_reason = "EX_DIVIDEND_RISK"
        
        # Execute exit
        if should_exit:
            self.Liquidate(self.ko)
            profit = pnl_pct * 100
            self.Log(f"EXIT KO ({exit_reason}): P&L = {profit:.2f}% after {days_held:.1f} days")
            
            # Reset tracking variables
            self.entry_price = 0
            self.position_entry_time = None
    
    def IsNearExDividend(self):
        """Check if we're near ex-dividend date (simplified)"""
        # KO typically pays quarterly dividends
        # This is simplified - in practice, use dividend calendar
        current_month = self.Time.month
        current_day = self.Time.day
        
        # Typical ex-dividend months and approximate dates
        ex_div_periods = [
            (3, 10, 20),   # March
            (6, 10, 20),   # June  
            (9, 10, 20),   # September
            (12, 10, 20)   # December
        ]
        
        for month, start_day, end_day in ex_div_periods:
            if current_month == month and start_day <= current_day <= end_day:
                return True
        
        return False
    
    def AllIndicatorsReady(self):
        """Check if all indicators are ready"""
        indicators = [
            self.ema_fast, self.ema_slow, self.ema_trend,
            self.rsi, self.macd, self.bb, self.volume_sma,
            self.price_sma_200, self.atr, self.sector_rsi
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Log final performance"""
        self.Log(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        algo_performance = (self.Portfolio.TotalPortfolioValue / 100000 - 1) * 100
        self.Log(f"KO Algorithm Performance: {algo_performance:.2f}%")