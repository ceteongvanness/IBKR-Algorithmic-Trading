# Import required QuantConnect modules
from AlgorithmImports import *

# Basic NVDA High Volatility Strategy for QuantConnect
# Simple template that should compile without errors

class HighVolatilityStrategy(QCAlgorithm):

    def Initialize(self):
        
        # Basic algorithm setup
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(1000)
        
        # Add NVDA
        self.nvda = self.AddEquity("NVDA", Resolution.Daily).Symbol
        self.SetBenchmark(self.nvda)
        
        # Simple parameters
        self.fast_period = 8
        self.slow_period = 21
        self.rsi_period = 14
        self.stop_loss = 0.08
        self.take_profit = 0.15
        
        # Technical indicators
        self.fast_ema = self.EMA(self.nvda, self.fast_period)
        self.slow_ema = self.EMA(self.nvda, self.slow_period)
        self.rsi_indicator = self.RSI(self.nvda, self.rsi_period)
        self.bb = self.BB(self.nvda, 20, 2.0)
        
        # Position tracking
        self.entry_price = 0
        self.days_held = 0
        self.max_days = 15
        
        # Performance tracking  
        self.trades = 0
        self.wins = 0
        
        # Warmup
        self.SetWarmUp(30)
        
    def OnData(self, slice):
        
        if self.IsWarmingUp:
            return
            
        # Check data availability
        if self.nvda not in slice:
            return
            
        # Get price safely
        try:
            current_price = slice[self.nvda].Price
        except:
            return
            
        if current_price <= 0:
            return
            
        # Check indicators ready
        if not (self.fast_ema.IsReady and self.slow_ema.IsReady and 
                self.rsi_indicator.IsReady and self.bb.IsReady):
            return
        
        # Get current position
        holdings = self.Portfolio[self.nvda]
        
        if holdings.Invested:
            self.ManagePosition(current_price)
        else:
            self.CheckEntry(current_price)
            
    def CheckEntry(self, price):
        
        # Simple entry signals
        ema_bullish = self.fast_ema.Current.Value > self.slow_ema.Current.Value
        rsi_oversold = self.rsi_indicator.Current.Value < 30
        price_near_lower_bb = price < self.bb.LowerBand.Current.Value * 1.02
        
        # Entry condition
        if ema_bullish and (rsi_oversold or price_near_lower_bb):
            
            # Calculate position size (keep it small for high volatility)
            portfolio_value = self.Portfolio.TotalPortfolioValue
            target_value = portfolio_value * 0.20  # 20% position
            
            shares = int(target_value / price)
            
            if shares > 0 and self.Portfolio.Cash >= shares * price:
                
                self.MarketOrder(self.nvda, shares)
                self.entry_price = price
                self.days_held = 0
                
                self.Debug(f"NVDA Long Entry: {shares} shares at ${price:.2f}")
                
    def ManagePosition(self, price):
        
        self.days_held += 1
        
        if self.entry_price <= 0:
            return
            
        # Calculate P&L
        pnl = (price - self.entry_price) / self.entry_price
        
        # Exit conditions
        should_exit = False
        exit_reason = ""
        
        # Stop loss
        if pnl <= -self.stop_loss:
            should_exit = True
            exit_reason = "Stop Loss"
            
        # Take profit  
        elif pnl >= self.take_profit:
            should_exit = True
            exit_reason = "Take Profit"
            
        # Time exit
        elif self.days_held >= self.max_days:
            should_exit = True
            exit_reason = "Time Limit"
            
        # Trend reversal
        elif self.fast_ema.Current.Value < self.slow_ema.Current.Value:
            should_exit = True
            exit_reason = "Trend Reversal"
            
        if should_exit:
            self.Liquidate(self.nvda)
            
            self.trades += 1
            if pnl > 0:
                self.wins += 1
                
            self.Debug(f"NVDA Exit: {exit_reason}, P&L: {pnl:.2%}")
            
            # Reset
            self.entry_price = 0
            self.days_held = 0
            
    def OnEndOfAlgorithm(self):
        
        final_value = self.Portfolio.TotalPortfolioValue
        total_return = (final_value - 1000) / 1000
        
        win_rate = self.wins / self.trades if self.trades > 0 else 0
        
        self.Log("=== NVDA STRATEGY RESULTS ===")
        self.Log(f"Final Value: ${final_value:.2f}")
        self.Log(f"Total Return: {total_return:.2%}")
        self.Log(f"Total Trades: {self.trades}")
        self.Log(f"Win Rate: {win_rate:.1%}")