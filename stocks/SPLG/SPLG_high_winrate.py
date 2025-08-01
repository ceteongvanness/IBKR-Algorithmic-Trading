from AlgorithmImports import *
import numpy as np

class HighWinRateSPLGStockAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash - optimized for smaller account
        self.SetCash(6319)  # Your current capital
        
        # Add SPLG (SPDR Portfolio S&P 500 ETF) - lower cost alternative to SPY
        self.splg = self.AddEquity("SPLG", Resolution.Minute).Symbol
        
        # Set benchmark to SPLG
        self.SetBenchmark(self.splg)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # Risk management parameters (optimized for small account)
        self.max_position_size = 0.90    # 90% max position for small account
        self.stop_loss_pct = 0.02        # 2% stop loss (tight risk control)
        self.take_profit_pct = 0.035     # 3.5% take profit (reasonable target)
        
        # Small account optimizations
        self.min_trade_value = 500       # Minimum $500 per trade
        self.max_trades_per_day = 2      # Limit trades to preserve capital
        self.daily_trade_count = 0
        
        # Trade management
        self.entry_price = 0
        self.position_entry_time = None
        self.min_hold_minutes = 45       # Slightly longer holds for stability
        
        # Market regime detection
        self.market_regime = "NEUTRAL"
        
        # Schedule functions
        self.Schedule.On(self.DateRules.EveryDay(self.splg), 
                        self.TimeRules.AfterMarketOpen(self.splg, 30), 
                        self.CheckMarketRegime)
        
        self.Schedule.On(self.DateRules.EveryDay(self.splg), 
                        self.TimeRules.AfterMarketOpen(self.splg, 5), 
                        self.ResetDailyCounters)
        
        # Warm up period
        self.SetWarmUp(100)
        
    def Setup_Indicators(self):
        # Trend indicators (optimized for SPLG characteristics)
        self.ema_fast = self.EMA(self.splg, 9, Resolution.Minute)    # Fast trend
        self.ema_slow = self.EMA(self.splg, 21, Resolution.Minute)   # Slow trend
        self.ema_trend = self.EMA(self.splg, 50, Resolution.Minute)  # Overall trend
        
        # Daily trend for higher timeframe context
        self.daily_ema = self.EMA(self.splg, 20, Resolution.Daily)
        
        # RSI for momentum
        self.rsi = self.RSI(self.splg, 14, Resolution.Minute)
        
        # MACD for trend confirmation
        self.macd = self.MACD(self.splg, 12, 26, 9, Resolution.Minute)
        
        # Bollinger Bands for volatility and mean reversion
        self.bb = self.BB(self.splg, 20, 2, Resolution.Minute)
        
        # Volume indicator
        self.volume_sma = self.SMA(self.splg, 20, Resolution.Minute, Field.Volume)
        
        # ATR for volatility-based position sizing
        self.atr = self.ATR(self.splg, 14, Resolution.Minute)
        
    def ResetDailyCounters(self):
        """Reset daily trade counter"""
        self.daily_trade_count = 0
        
    def CheckMarketRegime(self):
        """Determine market regime for SPLG"""
        if not self.daily_ema.IsReady:
            return
            
        current_price = self.Securities[self.splg].Price
        daily_ema_value = self.daily_ema.Current.Value
        
        # Market regime detection
        if current_price > daily_ema_value * 1.015:
            self.market_regime = "BULLISH"
        elif current_price < daily_ema_value * 0.985:
            self.market_regime = "BEARISH"
        else:
            self.market_regime = "NEUTRAL"
    
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        if not self.AllIndicatorsReady():
            return
            
        if not data.ContainsKey(self.splg):
            return
            
        current_price = data[self.splg].Close
        current_time = self.Time
        
        # Check for exit conditions first
        if self.Portfolio[self.splg].Invested:
            self.CheckExitConditions(current_price, current_time)
        else:
            # Look for entry opportunities (only if haven't exceeded daily limit)
            if self.daily_trade_count < self.max_trades_per_day:
                self.CheckEntryConditions(current_price, current_time, data)
    
    def CheckEntryConditions(self, current_price, current_time, data):
        """Entry conditions optimized for small account trading SPLG"""
        
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
        
        # Volume confirmation
        current_volume = data[self.splg].Volume
        avg_volume = self.volume_sma.Current.Value
        volume_spike = current_volume > avg_volume * 1.2
        
        # Calculate potential trade size
        available_capital = self.Portfolio.Cash
        max_trade_value = available_capital * self.max_position_size
        potential_shares = int(max_trade_value / current_price)
        trade_value = potential_shares * current_price
        
        # Skip if trade too small
        if trade_value < self.min_trade_value:
            return
        
        # Long entry conditions (high probability for small account)
        long_conditions = [
            # Trend alignment (critical for small accounts)
            ema_fast > ema_slow,
            current_price > ema_trend,
            current_price > self.daily_ema.Current.Value,
            
            # Market regime favorable
            self.market_regime in ["BULLISH", "NEUTRAL"],
            
            # Momentum conditions (conservative)
            rsi_value > 45 and rsi_value < 70,
            macd_value > macd_signal,
            
            # Mean reversion setup (buy dips in uptrend)
            current_price <= bb_middle * 1.01,
            current_price > bb_lower * 1.02,
            
            # Volume confirmation
            current_volume > avg_volume * 0.8,
            
            # Time filter (avoid first/last 30 minutes)
            current_time.hour >= 10 and current_time.hour < 15,
            
            # Risk management
            trade_value >= self.min_trade_value
        ]
        
        # Short entry conditions (more conservative for small account)
        short_conditions = [
            # Strong bearish alignment
            ema_fast < ema_slow,
            current_price < ema_trend,
            current_price < self.daily_ema.Current.Value * 0.99,
            
            # Market regime bearish
            self.market_regime == "BEARISH",
            
            # Momentum confirmation
            rsi_value < 55 and rsi_value > 30,
            macd_value < macd_signal,
            
            # Mean reversion setup
            current_price >= bb_middle * 0.99,
            current_price < bb_upper * 0.98,
            
            # Volume confirmation
            volume_spike,
            
            # Time filter
            current_time.hour >= 10 and current_time.hour < 15,
            
            # Risk management
            trade_value >= self.min_trade_value
        ]
        
        # Execute trades (require high conviction for small account)
        if sum(long_conditions) >= 9:  # High threshold for small account
            self.EnterLongPosition(current_price, potential_shares)
        elif sum(short_conditions) >= 8:  # Conservative short threshold
            self.EnterShortPosition(current_price, potential_shares)
    
    def EnterLongPosition(self, entry_price, shares):
        """Enter long position with small account optimization"""
        if shares > 0:
            self.MarketOrder(self.splg, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = shares * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"LONG SPLG: {shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%)")
    
    def EnterShortPosition(self, entry_price, shares):
        """Enter short position (conservative for small account)"""
        # Reduce short position size for small account
        short_shares = -int(shares * 0.7)  # 70% of long position size
        
        if short_shares < 0:
            self.MarketOrder(self.splg, short_shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.daily_trade_count += 1
            
            trade_value = abs(short_shares) * entry_price
            portfolio_pct = (trade_value / self.Portfolio.TotalPortfolioValue) * 100
            
            self.Log(f"SHORT SPLG: {short_shares} shares @ ${entry_price:.2f} (${trade_value:.0f}, {portfolio_pct:.1f}%)")
    
    def CheckExitConditions(self, current_price, current_time):
        """Exit conditions optimized for capital preservation"""
        position = self.Portfolio[self.splg]
        
        if position.Quantity == 0:
            return
            
        # Calculate P&L
        if position.IsLong:
            pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:
            pnl_pct = (self.entry_price - current_price) / self.entry_price
        
        # Time held
        minutes_held = (current_time - self.position_entry_time).total_seconds() / 60
        
        # Exit conditions
        should_exit = False
        exit_reason = ""
        
        # Take profit (tight for small account)
        if pnl_pct >= self.take_profit_pct:
            should_exit = True
            exit_reason = "TAKE_PROFIT"
        
        # Stop loss (tight risk control)
        elif pnl_pct <= -self.stop_loss_pct:
            should_exit = True
            exit_reason = "STOP_LOSS"
        
        # Time-based exits after minimum hold
        elif minutes_held >= self.min_hold_minutes:
            
            # Trend reversal exit
            if position.IsLong and self.ema_fast.Current.Value < self.ema_slow.Current.Value:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            elif position.IsShort and self.ema_fast.Current.Value > self.ema_slow.Current.Value:
                should_exit = True
                exit_reason = "TREND_REVERSAL"
            
            # RSI extreme exit
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
            
            # End of day exit
            elif current_time.hour >= 15 and current_time.minute >= 45:
                should_exit = True
                exit_reason = "END_OF_DAY"
        
        # Emergency exit for small account protection
        if pnl_pct <= -0.05:  # 5% emergency stop for small account
            should_exit = True
            exit_reason = "EMERGENCY_STOP"
        
        # Execute exit
        if should_exit:
            self.Liquidate(self.splg)
            profit = pnl_pct * 100
            trade_pnl = position.Quantity * (current_price - self.entry_price) if position.IsLong else position.Quantity * (self.entry_price - current_price)
            
            self.Log(f"EXIT SPLG ({exit_reason}): P&L = {profit:.2f}% (${trade_pnl:.2f}) after {minutes_held:.0f} min")
            
            # Reset tracking variables
            self.entry_price = 0
            self.position_entry_time = None
    
    def AllIndicatorsReady(self):
        """Check if all indicators are ready"""
        indicators = [
            self.ema_fast, self.ema_slow, self.ema_trend,
            self.rsi, self.macd, self.bb, self.volume_sma,
            self.daily_ema, self.atr
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Log final performance for small account"""
        final_value = self.Portfolio.TotalPortfolioValue
        initial_value = 6319
        total_return = (final_value - initial_value) / initial_value * 100
        
        self.Log(f"=== SPLG SMALL ACCOUNT PERFORMANCE ===")
        self.Log(f"Initial Capital: ${initial_value:,.2f}")
        self.Log(f"Final Portfolio Value: ${final_value:,.2f}")
        self.Log(f"Total Return: {total_return:.2f}%")
        self.Log(f"Absolute Profit/Loss: ${final_value - initial_value:,.2f}")