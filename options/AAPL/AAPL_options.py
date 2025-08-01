from AlgorithmImports import *
import numpy as np
from datetime import timedelta

class HighWinRateAAPLOptionsAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2022, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash
        self.SetCash(100000)
        
        # Add AAPL equity
        self.aapl = self.AddEquity("AAPL", Resolution.Minute).Symbol
        
        # Add AAPL options
        option = self.AddOption("AAPL", Resolution.Minute)
        self.aapl_option = option.Symbol
        
        # Set option filter
        option.SetFilter(self.OptionFilter)
        
        # Set benchmark
        self.SetBenchmark(self.aapl)
        
        # Initialize indicators for underlying
        self.Setup_Indicators()
        
        # Options strategy parameters
        self.max_dte = 45          # Maximum days to expiration
        self.min_dte = 7           # Minimum days to expiration
        self.target_delta = 0.30   # Target delta for short options
        self.profit_target = 0.50  # Take profit at 50% of max profit
        self.stop_loss = 2.0       # Stop loss at 200% of premium received
        
        # Position tracking
        self.active_positions = {}
        self.last_trade_time = datetime.min
        self.min_trade_interval = timedelta(hours=2)  # Minimum time between trades
        
        # Market regime detection
        self.market_regime = "NEUTRAL"
        self.volatility_regime = "NORMAL"
        
        # Schedule functions
        self.Schedule.On(self.DateRules.EveryDay(self.aapl), 
                        self.TimeRules.AfterMarketOpen(self.aapl, 30), 
                        self.DailyAnalysis)
        
        self.Schedule.On(self.DateRules.EveryDay(self.aapl), 
                        self.TimeRules.BeforeMarketClose(self.aapl, 30), 
                        self.ManagePositions)
        
        # Warm up period
        self.SetWarmUp(50)
        
    def Setup_Indicators(self):
        """Initialize technical indicators for underlying stock"""
        # Trend indicators
        self.ema_20 = self.EMA(self.aapl, 20, Resolution.Daily)
        self.ema_50 = self.EMA(self.aapl, 50, Resolution.Daily)
        
        # Volatility indicators
        self.bb = self.BB(self.aapl, 20, 2, Resolution.Daily)
        self.atr = self.ATR(self.aapl, 14, Resolution.Daily)
        
        # Momentum indicators
        self.rsi = self.RSI(self.aapl, 14, Resolution.Daily)
        
        # Volume
        self.volume_sma = self.SMA(self.aapl, 20, Resolution.Daily, Field.Volume)
        
        # Implied volatility rank proxy (using price volatility)
        self.volatility_window = RollingWindow[float](30)
        
    def OptionFilter(self, universe):
        """Filter options to trade"""
        return universe.IncludeWeeklys().Strikes(-10, 10).Expiration(timedelta(5), timedelta(60))
    
    def DailyAnalysis(self):
        """Analyze market conditions daily"""
        if not self.AllIndicatorsReady():
            return
            
        self.AnalyzeMarketRegime()
        self.AnalyzeVolatilityRegime()
    
    def AnalyzeMarketRegime(self):
        """Determine if market is bullish, bearish, or neutral"""
        current_price = self.Securities[self.aapl].Price
        ema_20_value = self.ema_20.Current.Value
        ema_50_value = self.ema_50.Current.Value
        rsi_value = self.rsi.Current.Value
        
        bullish_signals = 0
        bearish_signals = 0
        
        # Price vs EMAs
        if current_price > ema_20_value > ema_50_value:
            bullish_signals += 2
        elif current_price < ema_20_value < ema_50_value:
            bearish_signals += 2
            
        # RSI momentum
        if rsi_value > 60:
            bullish_signals += 1
        elif rsi_value < 40:
            bearish_signals += 1
            
        # Set regime
        if bullish_signals >= 2 and bullish_signals > bearish_signals:
            self.market_regime = "BULLISH"
        elif bearish_signals >= 2 and bearish_signals > bullish_signals:
            self.market_regime = "BEARISH"
        else:
            self.market_regime = "NEUTRAL"
    
    def AnalyzeVolatilityRegime(self):
        """Analyze current volatility environment"""
        if len(self.volatility_window) < 20:
            return
            
        current_price = self.Securities[self.aapl].Price
        bb_width = (self.bb.UpperBand.Current.Value - self.bb.LowerBand.Current.Value) / self.bb.MiddleBand.Current.Value
        
        # Calculate recent volatility
        recent_volatility = np.std([x for x in self.volatility_window[:20]]) * np.sqrt(252)
        
        if bb_width > 0.08:  # Wide Bollinger Bands indicate high volatility
            self.volatility_regime = "HIGH"
        elif bb_width < 0.04:  # Narrow Bollinger Bands indicate low volatility
            self.volatility_regime = "LOW"
        else:
            self.volatility_regime = "NORMAL"
    
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        # Update volatility window
        if self.aapl in data and data[self.aapl] is not None:
            price_change = (data[self.aapl].Close / data[self.aapl].Open - 1) if data[self.aapl].Open != 0 else 0
            self.volatility_window.Add(price_change)
        
        # Manage existing positions first
        self.ManageExistingPositions(data)
        
        # Look for new trading opportunities
        if self.CanTrade() and self.AllIndicatorsReady():
            self.LookForTrades(data)
    
    def CanTrade(self):
        """Check if we can enter new trades"""
        # Don't trade too frequently
        if self.Time - self.last_trade_time < self.min_trade_interval:
            return False
            
        # Don't have too many active positions
        if len(self.active_positions) >= 3:
            return False
            
        # Avoid trading in first/last 30 minutes
        if self.Time.hour < 10 or (self.Time.hour >= 15 and self.Time.minute >= 30):
            return False
            
        return True
    
    def LookForTrades(self, data):
        """Look for high-probability options trades"""
        
        # Get options chain
        chain = data.OptionChains.get(self.aapl_option)
        if not chain:
            return
            
        # Filter options by our criteria
        calls, puts = self.FilterOptionsChain(chain)
        
        # Determine strategy based on market conditions
        if self.market_regime == "BULLISH" and self.volatility_regime in ["HIGH", "NORMAL"]:
            # Sell cash-secured puts in bullish market with decent volatility
            self.TradeCashSecuredPuts(puts)
            
        elif self.market_regime == "BEARISH" and self.volatility_regime in ["HIGH", "NORMAL"]:
            # Sell covered calls in bearish market
            self.TradeCoveredCalls(calls)
            
        elif self.market_regime == "NEUTRAL" and self.volatility_regime == "HIGH":
            # Sell strangles in neutral market with high volatility
            self.TradeShortStrangles(calls, puts)
            
        elif self.volatility_regime == "LOW":
            # Buy options when volatility is low (expecting expansion)
            self.TradeLongOptions(calls, puts)
    
    def FilterOptionsChain(self, chain):
        """Filter options chain for trading candidates"""
        calls = []
        puts = []
        
        current_price = self.Securities[self.aapl].Price
        
        for contract in chain:
            # Days to expiration check
            days_to_expiry = (contract.Expiry.date() - self.Time.date()).days
            if days_to_expiry < self.min_dte or days_to_expiry > self.max_dte:
                continue
                
            # Liquidity check (basic)
            if contract.BidPrice <= 0 or contract.AskPrice <= 0:
                continue
                
            # Bid-ask spread check
            if contract.AskPrice > 0 and (contract.AskPrice - contract.BidPrice) / contract.AskPrice > 0.1:
                continue
                
            # Delta check for short options
            if abs(contract.Greeks.Delta) < 0.15 or abs(contract.Greeks.Delta) > 0.45:
                continue
                
            if contract.Right == OptionRight.Call:
                calls.append(contract)
            else:
                puts.append(contract)
        
        return calls, puts
    
    def TradeCashSecuredPuts(self, puts):
        """Trade cash-secured puts - high win rate strategy"""
        current_price = self.Securities[self.aapl].Price
        
        # Find puts around 0.30 delta (out of the money)
        target_puts = [p for p in puts if 0.25 <= abs(p.Greeks.Delta) <= 0.35 and p.Strike < current_price * 0.95]
        
        if not target_puts:
            return
            
        # Select the put with best risk/reward
        best_put = max(target_puts, key=lambda x: x.BidPrice / (current_price - x.Strike))
        
        # Calculate position size
        cash_required = best_put.Strike * 100  # Cash secured put requires cash for 100 shares
        max_contracts = int(self.Portfolio.Cash * 0.3 / cash_required)  # Use max 30% of cash
        
        if max_contracts >= 1:
            # Sell puts
            contracts_to_sell = min(max_contracts, 2)  # Max 2 contracts per trade
            self.MarketOrder(best_put.Symbol, -contracts_to_sell)
            
            # Track position
            self.active_positions[best_put.Symbol] = {
                'type': 'CASH_SECURED_PUT',
                'entry_price': best_put.BidPrice,
                'entry_time': self.Time,
                'contracts': contracts_to_sell,
                'strike': best_put.Strike,
                'expiry': best_put.Expiry
            }
            
            self.last_trade_time = self.Time
            self.Log(f"SOLD {contracts_to_sell} Cash-Secured Puts: {best_put.Strike} @ ${best_put.BidPrice:.2f}")
    
    def TradeCoveredCalls(self, calls):
        """Trade covered calls if we own the stock"""
        if self.Portfolio[self.aapl].Quantity < 100:
            return  # Need at least 100 shares for covered call
            
        current_price = self.Securities[self.aapl].Price
        
        # Find calls around 0.30 delta (out of the money)
        target_calls = [c for c in calls if 0.25 <= c.Greeks.Delta <= 0.35 and c.Strike > current_price * 1.05]
        
        if not target_calls:
            return
            
        # Select the call with best premium
        best_call = max(target_calls, key=lambda x: x.BidPrice)
        
        # Calculate how many contracts we can sell
        shares_owned = self.Portfolio[self.aapl].Quantity
        max_contracts = int(shares_owned / 100)
        
        if max_contracts >= 1:
            contracts_to_sell = min(max_contracts, 2)
            self.MarketOrder(best_call.Symbol, -contracts_to_sell)
            
            # Track position
            self.active_positions[best_call.Symbol] = {
                'type': 'COVERED_CALL',
                'entry_price': best_call.BidPrice,
                'entry_time': self.Time,
                'contracts': contracts_to_sell,
                'strike': best_call.Strike,
                'expiry': best_call.Expiry
            }
            
            self.last_trade_time = self.Time
            self.Log(f"SOLD {contracts_to_sell} Covered Calls: {best_call.Strike} @ ${best_call.BidPrice:.2f}")
    
    def TradeShortStrangles(self, calls, puts):
        """Trade short strangles in high volatility neutral markets"""
        current_price = self.Securities[self.aapl].Price
        
        # Find equidistant calls and puts
        target_calls = [c for c in calls if 0.25 <= c.Greeks.Delta <= 0.35]
        target_puts = [p for p in puts if -0.35 <= p.Greeks.Delta <= -0.25]
        
        if not target_calls or not target_puts:
            return
            
        # Select strikes roughly equidistant from current price
        best_call = min(target_calls, key=lambda x: abs(x.Strike - current_price * 1.1))
        best_put = min(target_puts, key=lambda x: abs(x.Strike - current_price * 0.9))
        
        # Check if we have same expiration
        if best_call.Expiry != best_put.Expiry:
            return
            
        # Calculate total premium
        total_premium = best_call.BidPrice + best_put.BidPrice
        
        if total_premium > 2.0:  # Minimum premium threshold
            # Sell strangle
            self.MarketOrder(best_call.Symbol, -1)
            self.MarketOrder(best_put.Symbol, -1)
            
            # Track positions
            position_id = f"STRANGLE_{self.Time.strftime('%Y%m%d_%H%M')}"
            self.active_positions[position_id] = {
                'type': 'SHORT_STRANGLE',
                'call_symbol': best_call.Symbol,
                'put_symbol': best_put.Symbol,
                'entry_premium': total_premium,
                'entry_time': self.Time,
                'call_strike': best_call.Strike,
                'put_strike': best_put.Strike,
                'expiry': best_call.Expiry
            }
            
            self.last_trade_time = self.Time
            self.Log(f"SOLD Strangle: Call {best_call.Strike} Put {best_put.Strike} @ ${total_premium:.2f}")
    
    def TradeLongOptions(self, calls, puts):
        """Buy options when volatility is low"""
        if self.market_regime == "BULLISH":
            # Buy calls
            atm_calls = [c for c in calls if abs(c.Greeks.Delta - 0.5) < 0.1]
            if atm_calls:
                best_call = min(atm_calls, key=lambda x: x.AskPrice)
                self.MarketOrder(best_call.Symbol, 1)
                
                self.active_positions[best_call.Symbol] = {
                    'type': 'LONG_CALL',
                    'entry_price': best_call.AskPrice,
                    'entry_time': self.Time,
                    'contracts': 1,
                    'strike': best_call.Strike,
                    'expiry': best_call.Expiry
                }
                
                self.last_trade_time = self.Time
                self.Log(f"BOUGHT Call: {best_call.Strike} @ ${best_call.AskPrice:.2f}")
                
        elif self.market_regime == "BEARISH":
            # Buy puts
            atm_puts = [p for p in puts if abs(abs(p.Greeks.Delta) - 0.5) < 0.1]
            if atm_puts:
                best_put = min(atm_puts, key=lambda x: x.AskPrice)
                self.MarketOrder(best_put.Symbol, 1)
                
                self.active_positions[best_put.Symbol] = {
                    'type': 'LONG_PUT',
                    'entry_price': best_put.AskPrice,
                    'entry_time': self.Time,
                    'contracts': 1,
                    'strike': best_put.Strike,
                    'expiry': best_put.Expiry
                }
                
                self.last_trade_time = self.Time
                self.Log(f"BOUGHT Put: {best_put.Strike} @ ${best_put.AskPrice:.2f}")
    
    def ManageExistingPositions(self, data):
        """Manage existing option positions"""
        positions_to_close = []
        
        for position_id, position_info in self.active_positions.items():
            should_close, reason = self.ShouldClosePosition(position_info, data)
            
            if should_close:
                self.ClosePosition(position_id, position_info, reason)
                positions_to_close.append(position_id)
        
        # Remove closed positions
        for position_id in positions_to_close:
            del self.active_positions[position_id]
    
    def ShouldClosePosition(self, position_info, data):
        """Determine if a position should be closed"""
        # Days to expiration check
        days_to_expiry = (position_info['expiry'].date() - self.Time.date()).days
        
        if days_to_expiry <= 2:
            return True, "EXPIRATION"
        
        # For short options (premium collection strategies)
        if position_info['type'] in ['CASH_SECURED_PUT', 'COVERED_CALL']:
            symbol = None
            for key in position_info:
                if 'symbol' in key.lower() or key == 'symbol':
                    symbol = position_info[key]
                    break
            
            if symbol and symbol in data and data[symbol]:
                current_price = data[symbol].Price
                entry_price = position_info['entry_price']
                
                # Take profit at 50% of max profit
                if current_price <= entry_price * self.profit_target:
                    return True, "PROFIT_TARGET"
                
                # Stop loss at 200% of premium received
                if current_price >= entry_price * self.stop_loss:
                    return True, "STOP_LOSS"
        
        return False, ""
    
    def ClosePosition(self, position_id, position_info, reason):
        """Close an option position"""
        try:
            if position_info['type'] == 'SHORT_STRANGLE':
                # Close strangle
                self.MarketOrder(position_info['call_symbol'], 1)
                self.MarketOrder(position_info['put_symbol'], 1)
                self.Log(f"CLOSED Strangle ({reason})")
                
            elif position_info['type'] in ['CASH_SECURED_PUT', 'COVERED_CALL']:
                # Close single option
                contracts = position_info['contracts']
                symbol = position_info.get('symbol')
                if symbol:
                    self.MarketOrder(symbol, contracts)  # Buy back short position
                    self.Log(f"CLOSED {position_info['type']} ({reason})")
                    
            elif position_info['type'] in ['LONG_CALL', 'LONG_PUT']:
                # Close long option
                symbol = position_info.get('symbol')
                if symbol:
                    self.MarketOrder(symbol, -1)  # Sell long position
                    self.Log(f"CLOSED {position_info['type']} ({reason})")
                    
        except Exception as e:
            self.Log(f"Error closing position {position_id}: {str(e)}")
    
    def ManagePositions(self):
        """Daily position management"""
        # Check for positions near expiration
        for position_id, position_info in list(self.active_positions.items()):
            days_to_expiry = (position_info['expiry'].date() - self.Time.date()).days
            
            if days_to_expiry <= 5:
                self.Log(f"Position {position_id} expiring in {days_to_expiry} days")
    
    def AllIndicatorsReady(self):
        """Check if all indicators are ready"""
        indicators = [self.ema_20, self.ema_50, self.bb, self.rsi, self.atr, self.volume_sma]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Log final performance"""
        self.Log(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        algo_performance = (self.Portfolio.TotalPortfolioValue / 100000 - 1) * 100
        self.Log(f"Algorithm Performance: {algo_performance:.2f}%")
        self.Log(f"Active Positions at End: {len(self.active_positions)}")