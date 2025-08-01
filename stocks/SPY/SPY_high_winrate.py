from AlgorithmImports import *
import numpy as np

class HighWinRateSPYAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash
        self.SetCash(100000)
        
        # Add SPY with minute resolution for better entry/exit timing
        self.spy = self.AddEquity("SPY", Resolution.Minute).Symbol
        
        # Set benchmark to SPY
        self.SetBenchmark(self.spy)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # Risk management parameters
        self.max_position_size = 0.95  # Maximum 95% of portfolio
        self.stop_loss_pct = 0.015     # 1.5% stop loss
        self.take_profit_pct = 0.025   # 2.5% take profit (higher than stop for positive R:R)
        
        # Trade management
        self.entry_price = 0
        self.position_entry_time = None
        self.min_hold_minutes = 30  # Minimum hold time to avoid whipsaws
        
        # Market regime detection
        self.market_regime = "NEUTRAL"
        
        # Schedule functions
        self.Schedule.On(self.DateRules.EveryDay(self.spy), 
                        self.TimeRules.AfterMarketOpen(self.spy, 30), 
                        self.CheckMarketRegime)
        
        # Warm up period
        self.SetWarmUp(200)
        
    def Setup_Indicators(self):
        # Multiple timeframe analysis
        self.ema_fast = self.EMA(self.spy, 12, Resolution.Minute)
        self.ema_slow = self.EMA(self.spy, 26, Resolution.Minute)
        self.ema_trend = self.EMA(self.spy, 50, Resolution.Minute)
        
        # RSI for momentum
        self.rsi = self.RSI(self.spy, 14, Resolution.Minute)
        
        # MACD for trend confirmation
        self.macd = self.MACD(self.spy, 12, 26, 9, Resolution.Minute)
        
        # Bollinger Bands for volatility
        self.bb = self.BB(self.spy, 20, 2, Resolution.Minute)
        
        # Volume indicator
        self.volume_sma = self.SMA(self.spy, 20, Resolution.Minute, Field.Volume)
        
        # Higher timeframe trend (daily)
        self.daily_ema = self.EMA(self.spy, 20, Resolution.Daily)
        
        # ATR for position sizing
        self.atr = self.ATR(self.spy, 14, Resolution.Minute)
        
    def CheckMarketRegime(self):
        """Determine market regime for better trade selection"""
        if not self.daily_ema.IsReady:
            return
            
        current_price = self.Securities[self.spy].Price
        daily_ema_value = self.daily_ema.Current.Value
        
        # Simple regime detection
        if current_price > daily_ema_value * 1.02:
            self.market_regime = "BULLISH"
        elif current_price < daily_ema_value * 0.98:
            self.market_regime = "BEARISH"
        else:
            self.market_regime = "NEUTRAL"
    
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        if not self.AllIndicatorsReady():
            return
            
        if not data.ContainsKey(self.spy):
            return
            
        current_price = data[self.spy].Close
        current_time = self.Time
        
        # Check for exit conditions first
        if self.Portfolio[self.spy].Invested:
            self.CheckExitConditions(current_price, current_time)
        else:
            # Look for entry opportunities
            self.CheckEntryConditions(current_price, current_time, data)
    
    def CheckEntryConditions(self, current_price, current_time, data):
        """High probability entry conditions"""
        
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
        current_volume = data[self.spy].Volume
        avg_volume = self.volume_sma.Current.Value
        volume_spike = current_volume > avg_volume * 1.2
        
        # Long entry conditions (high probability)
        long_conditions = [
            # Trend alignment
            ema_fast > ema_slow,  # Short term uptrend
            current_price > ema_trend,  # Above medium term trend
            self.market_regime in ["BULLISH", "NEUTRAL"],  # Favorable regime
            
            # Momentum conditions
            rsi_value > 45 and rsi_value < 70,  # Not oversold, not overbought
            macd_value > macd_signal,  # MACD bullish
            
            # Mean reversion component (buy dips in uptrend)
            current_price < bb_middle * 1.005,  # Near or below BB middle
            current_price > bb_lower * 1.01,   # But not at extreme lows
            
            # Volume confirmation
            volume_spike or current_volume > avg_volume * 0.8
        ]
        
        # Short entry conditions (high probability)
        short_conditions = [
            # Trend alignment
            ema_fast < ema_slow,  # Short term downtrend
            current_price < ema_trend,  # Below medium term trend
            self.market_regime in ["BEARISH", "NEUTRAL"],  # Favorable regime
            
            # Momentum conditions
            rsi_value < 55 and rsi_value > 30,  # Not overbought, not oversold
            macd_value < macd_signal,  # MACD bearish
            
            # Mean reversion component (sell rallies in downtrend)
            current_price > bb_middle * 0.995,  # Near or above BB middle
            current_price < bb_upper * 0.99,   # But not at extreme highs
            
            # Volume confirmation
            volume_spike or current_volume > avg_volume * 0.8
        ]
        
        # Execute trades with high conviction
        if sum(long_conditions) >= 6:  # Require most conditions to be met
            self.EnterLongPosition(current_price)
        elif sum(short_conditions) >= 6:  # Require most conditions to be met
            self.EnterShortPosition(current_price)
    
    def EnterLongPosition(self, entry_price):
        """Enter long position with proper sizing"""
        # Position sizing based on ATR
        atr_value = self.atr.Current.Value
        risk_per_share = max(atr_value * 1.5, entry_price * self.stop_loss_pct)
        
        # Calculate position size based on risk
        portfolio_risk = self.Portfolio.TotalPortfolioValue * 0.02  # Risk 2% of portfolio
        shares = int(portfolio_risk / risk_per_share)
        
        # Limit position size
        max_shares = int(self.Portfolio.TotalPortfolioValue * self.max_position_size / entry_price)
        shares = min(shares, max_shares)
        
        if shares > 0:
            self.MarketOrder(self.spy, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.Log(f"LONG: {shares} shares at ${entry_price:.2f}")
    
    def EnterShortPosition(self, entry_price):
        """Enter short position with proper sizing"""
        # Position sizing based on ATR
        atr_value = self.atr.Current.Value
        risk_per_share = max(atr_value * 1.5, entry_price * self.stop_loss_pct)
        
        # Calculate position size based on risk
        portfolio_risk = self.Portfolio.TotalPortfolioValue * 0.02  # Risk 2% of portfolio
        shares = -int(portfolio_risk / risk_per_share)
        
        # Limit position size
        max_shares = -int(self.Portfolio.TotalPortfolioValue * self.max_position_size / entry_price)
        shares = max(shares, max_shares)
        
        if shares < 0:
            self.MarketOrder(self.spy, shares)
            self.entry_price = entry_price
            self.position_entry_time = self.Time
            self.Log(f"SHORT: {shares} shares at ${entry_price:.2f}")
    
    def CheckExitConditions(self, current_price, current_time):
        """Exit conditions to maximize win rate"""
        position = self.Portfolio[self.spy]
        
        if position.Quantity == 0:
            return
            
        # Calculate P&L
        if position.IsLong:
            pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:
            pnl_pct = (self.entry_price - current_price) / self.entry_price
        
        # Time-based exit (avoid holding too long)
        minutes_held = (current_time - self.position_entry_time).total_seconds() / 60
        
        # Exit conditions
        should_exit = False
        exit_reason = ""
        
        # Take profit (higher than stop loss for better win rate)
        if pnl_pct >= self.take_profit_pct:
            should_exit = True
            exit_reason = "TAKE_PROFIT"
        
        # Stop loss
        elif pnl_pct <= -self.stop_loss_pct:
            should_exit = True
            exit_reason = "STOP_LOSS"
        
        # Time-based exit after minimum hold
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
            
            # End of day exit (avoid overnight risk)
            elif current_time.hour >= 15 and current_time.minute >= 45:
                should_exit = True
                exit_reason = "END_OF_DAY"
        
        # Execute exit
        if should_exit:
            self.Liquidate(self.spy)
            profit = pnl_pct * 100
            self.Log(f"EXIT ({exit_reason}): P&L = {profit:.2f}% after {minutes_held:.0f} minutes")
            
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
        """Log final performance"""
        self.Log(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        
        # Log final benchmark comparison
        algo_performance = (self.Portfolio.TotalPortfolioValue / 100000 - 1) * 100
        self.Log(f"Algorithm Performance: {algo_performance:.2f}%")