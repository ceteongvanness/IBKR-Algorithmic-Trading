from AlgorithmImports import *
import numpy as np
from datetime import timedelta

class HighWinRateMSFTOptionsAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2022, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash
        self.SetCash(6319)  # Your current capital
        
        # Add MSFT equity
        self.msft = self.AddEquity("MSFT", Resolution.Minute).Symbol
        
        # Add MSFT options
        option = self.AddOption("MSFT", Resolution.Minute)
        self.msft_option = option.Symbol
        
        # Set option filter for blue-chip tech stock
        option.SetFilter(self.OptionFilter)
        
        # Set benchmark
        self.SetBenchmark(self.msft)
        
        # Initialize indicators for underlying
        self.Setup_Indicators()
        
        # Options strategy parameters (optimized for blue-chip tech)
        self.max_dte = 50              # Maximum days to expiration
        self.min_dte = 7               # Minimum days to expiration  
        self.target_delta_low = 0.25   # Conservative delta for shorts
        self.target_delta_high = 0.40  # Maximum delta for shorts
        self.profit_target = 0.55      # Take profit at 55%
        self.stop_loss = 2.5           # Stop loss at 250% (conservative)
        
        # Position tracking
        self.active_positions = {}
        self.last_trade_time = datetime.min
        self.min_trade_interval = timedelta(hours=3)  # 3 hour minimum between trades
        
        # Market and tech sector awareness
        self.market_regime = "NEUTRAL"
        self.volatility_regime = "NORMAL"
        self.tech_earnings_season = False
        self.msft_earnings_proximity = "CLEAR"
        
        # Schedule functions
        self.Schedule.On(self.DateRules.EveryDay(self.msft), 
                        self.TimeRules.AfterMarketOpen(self.msft, 30), 
                        self.DailyAnalysis)
        
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday), 
                        self.TimeRules.AfterMarketOpen(self.msft, 60), 
                        self.WeeklyTechAnalysis)
        
        # Warm up period
        self.SetWarmUp(100)
        
    def Setup_Indicators(self):
        """Initialize technical indicators for MSFT"""
        # Trend indicators (blue-chip tech optimized)
        self.ema_20 = self.EMA(self.msft, 20, Resolution.Daily)
        self.ema_50 = self.EMA(self.msft, 50, Resolution.Daily)
        self.sma_200 = self.SMA(self.msft, 200, Resolution.Daily)
        
        # Volatility indicators
        self.bb = self.BB(self.msft, 20, 2, Resolution.Daily)
        self.atr = self.ATR(self.msft, 14, Resolution.Daily)
        
        # Momentum indicators
        self.rsi = self.RSI(self.msft, 14, Resolution.Daily)
        
        # Volume (institutional flow important for options)
        self.volume_sma = self.SMA(self.msft, 20, Resolution.Daily, Field.Volume)
        
        # Tech sector strength
        self.tech_momentum = self.RSI(self.msft, 21, Resolution.Weekly)
        
        # Volatility regime detection
        self.volatility_window = RollingWindow[float](30)
        
    def OptionFilter(self, universe):
        """Filter options for blue-chip tech stock"""
        return universe.IncludeWeeklys().Strikes(-10, 10).Expiration(timedelta(5), timedelta(60))
    
    def DailyAnalysis(self):
        """Daily analysis for MSFT options"""
        if not self.AllIndicatorsReady():
            return
            
        self.AnalyzeMarketRegime()
        self.AnalyzeVolatilityRegime()
        self.CheckEarningsProximity()
    
    def AnalyzeMarketRegime(self):
        """Market regime analysis for blue-chip tech"""
        current_price = self.Securities[self.msft].Price
        ema_20_value = self.ema_20.Current.Value
        ema_50_value = self.ema_50.Current.Value
        sma_200_value = self.sma_200.Current.Value
        rsi_value = self.rsi.Current.Value
        
        bullish_signals = 0
        bearish_signals = 0
        
        # Long-term trend (critical for tech leadership)
        if current_price > sma_200_value * 1.02:
            bullish_signals += 3
        elif current_price < sma_200_value * 0.98:
            bearish_signals += 3
            
        # Medium-term trend
        if current_price > ema_50_value and ema_20_value > ema_50_value:
            bullish_signals += 2
        elif current_price < ema_50_value and ema_20_value < ema_50_value:
            bearish_signals += 2
            
        # Momentum
        if rsi_value > 55:
            bullish_signals += 1
        elif rsi_value < 45:
            bearish_signals += 1
            
        # Set regime
        if bullish_signals >= 4 and bullish_signals > bearish_signals:
            self.market_regime = "BULLISH"
        elif bearish_signals >= 4 and bearish_signals > bullish_signals:
            self.market_regime = "BEARISH"
        else:
            self.market_regime = "NEUTRAL"
    
    def AnalyzeVolatilityRegime(self):
        """Analyze volatility for options strategy selection"""
        current_price = self.Securities[self.msft].Price
        bb_width = (self.bb.UpperBand.Current.Value - self.bb.LowerBand.Current.Value) / self.bb.MiddleBand.Current.Value
        
        # Update volatility window
        if current_price > 0:
            daily_return = (current_price / self.Securities[self.msft].Close - 1) if hasattr(self.Securities[self.msft], 'Close') else 0
            self.volatility_window.Add(abs(daily_return))
        
        # Volatility regime classification
        if bb_width > 0.06:  # Wide Bollinger Bands
            self.volatility_regime = "HIGH"
        elif bb_width < 0.03:  # Narrow Bollinger Bands
            self.volatility_regime = "LOW"
        else:
            self.volatility_regime = "NORMAL"
    
    def CheckEarningsProximity(self):
        """Check proximity to MSFT earnings"""
        current_month = self.Time.month
        current_day = self.Time.day
        
        # MSFT earnings months: January, April, July, October
        earnings_months = [1, 4, 7, 10]
        
        if current_month in earnings_months:
            if 15 <= current_day <= 30:
                self.msft_earnings_proximity = "NEAR"
            else:
                self.msft_earnings_proximity = "CLEAR"
        else:
            self.msft_earnings_proximity = "CLEAR"
    
    def WeeklyTechAnalysis(self):
        """Weekly tech sector analysis"""
        if not self.tech_momentum.IsReady:
            return
            
        tech_rsi = self.tech_momentum.Current.Value
        
        # Check if it's tech earnings season (quarterly)
        current_month = self.Time.month
        if current_month in [1, 4, 7, 10]:  # Earnings months
            self.tech_earnings_season = True
        else:
            self.tech_earnings_season = False
    
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        # Manage existing positions first
        self.ManageExistingPositions(data)
        
        # Look for new trading opportunities
        if self.CanTrade() and self.AllIndicatorsReady():
            self.LookForTrades(data)
    
    def CanTrade(self):
        """Enhanced trade filtering for blue-chip options"""
        # Standard checks
        if self.Time - self.last_trade_time < self.min_trade_interval:
            return False
            
        if len(self.active_positions) >= 2:  # Conservative limit for options
            return False
            
        if self.Time.hour < 10 or (self.Time.hour >= 15 and self.Time.minute >= 30):
            return False
        
        # Tech-specific checks
        if self.msft_earnings_proximity == "NEAR" and self.tech_earnings_season:
            return False  # Extra cautious during tech earnings season
            
        return True
    
    def LookForTrades(self, data):
        """Look for MSFT options trading opportunities"""
        chain = data.OptionChains.get(self.msft_option)
        if not chain:
            return
            
        calls, puts = self.FilterOptionsChain(chain)
        
        # Strategy selection based on market conditions and volatility
        if self.market_regime == "BULLISH" and self.volatility_regime in ["NORMAL", "HIGH"]:
            # Primary: Cash-secured puts in bullish tech environment
            self.TradeCashSecuredPuts(puts)
            
        elif self.market_regime == "NEUTRAL" and self.volatility_regime == "HIGH":
            # Secondary: Short strangles in neutral high-vol environment
            self.TradeShortStrangles(calls, puts)
            
        elif self.market_regime == "BEARISH" and self.Portfolio[self.msft].Quantity >= 100:
            # Defensive: Covered calls if we own stock
            self.TradeCoveredCalls(calls)
            
        elif self.volatility_regime == "LOW" and self.market_regime != "BEARISH":
            # Volatility expansion: Long options when vol is compressed
            self.TradeLongOptions(calls, puts)
    
    def FilterOptionsChain(self, chain):
        """Filter options chain for MSFT characteristics"""
        calls = []
        puts = []
        
        current_price = self.Securities[self.msft].Price
        
        for contract in chain:
            # Days to expiration
            days_to_expiry = (contract.Expiry.date() - self.Time.date()).days
            if days_to_expiry < self.min_dte or days_to_expiry > self.max_dte:
                continue
                
            # Liquidity check
            if contract.BidPrice <= 0 or contract.AskPrice <= 0:
                continue
                
            # Bid-ask spread check (tighter for MSFT)
            if contract.AskPrice > 0 and (contract.AskPrice - contract.BidPrice) / contract.AskPrice > 0.08:
                continue
                
            # Delta filtering
            if abs(contract.Greeks.Delta) < 0.20 or abs(contract.Greeks.Delta) > 0.50:
                continue
                
            # Minimum premium for MSFT
            if contract.BidPrice < 0.25:
                continue
                
            if contract.Right == OptionRight.Call:
                calls.append(contract)
            else:
                puts.append(contract)
        
        return calls, puts
    
    def TradeCashSecuredPuts(self, puts):
        """Primary strategy: Cash-secured puts for MSFT"""
        current_price = self.Securities[self.msft].Price
        
        # Find puts with target delta
        target_puts = [p for p in puts 
                      if self.target_delta_low <= abs(p.Greeks.Delta) <= self.target_delta_high 
                      and p.Strike < current_price * 0.95]
        
        if not target_puts:
            return
            
        # Select put with best risk-adjusted premium
        best_put = max(target_puts, key=lambda x: x.BidPrice / (current_price - x.Strike) if current_price > x.Strike else 0)
        
        # Calculate position size
        cash_required = best_put.Strike * 100
        max_contracts = int(self.Portfolio.Cash * 0.4 / cash_required)  # Use 40% of cash
        
        if max_contracts >= 1:
            contracts_to_sell = min(max_contracts, 1)  # Conservative: 1 contract
            self.MarketOrder(best_put.Symbol, -contracts_to_sell)
            
            # Track position
            self.active_positions[best_put.Symbol] = {
                'type': 'CASH_SECURED_PUT',
                'entry_price': best_put.BidPrice,
                'entry_time': self.Time,
                'contracts': contracts_to_sell,
                'strike': best_put.Strike,
                'expiry': best_put.Expiry,
                'underlying_price': current_price
            }
            
            self.last_trade_time = self.Time
            self.Log(f"SOLD MSFT Cash-Secured Put: ${best_put.Strike} @ ${best_put.BidPrice:.2f}")
    
    def TradeCoveredCalls(self, calls):
        """Covered calls strategy for MSFT stock holdings"""
        if self.Portfolio[self.msft].Quantity < 100:
            return
            
        current_price = self.Securities[self.msft].Price
        
        # Find calls with conservative delta
        target_calls = [c for c in calls 
                       if self.target_delta_low <= c.Greeks.Delta <= 0.35  # Conservative for blue-chip
                       and c.Strike > current_price * 1.03]
        
        if not target_calls:
            return
            
        # Select call with best premium
        best_call = max(target_calls, key=lambda x: x.BidPrice)
        
        # Calculate contracts
        shares_owned = self.Portfolio[self.msft].Quantity
        max_contracts = int(shares_owned / 100)
        
        if max_contracts >= 1:
            contracts_to_sell = min(max_contracts, 1)
            self.MarketOrder(best_call.Symbol, -contracts_to_sell)
            
            # Track position
            self.active_positions[best_call.Symbol] = {
                'type': 'COVERED_CALL',
                'entry_price': best_call.BidPrice,
                'entry_time': self.Time,
                'contracts': contracts_to_sell,
                'strike': best_call.Strike,
                'expiry': best_call.Expiry,
                'underlying_price': current_price
            }
            
            self.last_trade_time = self.Time
            self.Log(f"SOLD MSFT Covered Call: ${best_call.Strike} @ ${best_call.BidPrice:.2f}")
    
    def TradeShortStrangles(self, calls, puts):
        """Short strangles for neutral high-volatility periods"""
        current_price = self.Securities[self.msft].Price
        
        # Find balanced strikes
        target_calls = [c for c in calls if 0.25 <= c.Greeks.Delta <= 0.35]
        target_puts = [p for p in puts if -0.35 <= p.Greeks.Delta <= -0.25]
        
        if not target_calls or not target_puts:
            return
            
        # Select strikes roughly equidistant
        best_call = min(target_calls, key=lambda x: abs(x.Strike - current_price * 1.08))
        best_put = min(target_puts, key=lambda x: abs(x.Strike - current_price * 0.92))
        
        # Same expiration required
        if best_call.Expiry != best_put.Expiry:
            return
            
        total_premium = best_call.BidPrice + best_put.BidPrice
        if total_premium < 1.5:  # Minimum premium for MSFT
            return
            
        # Execute strangle
        self.MarketOrder(best_call.Symbol, -1)
        self.MarketOrder(best_put.Symbol, -1)
        
        # Track position
        position_id = f"MSFT_STRANGLE_{self.Time.strftime('%Y%m%d_%H%M')}"
        self.active_positions[position_id] = {
            'type': 'SHORT_STRANGLE',
            'call_symbol': best_call.Symbol,
            'put_symbol': best_put.Symbol,
            'entry_premium': total_premium,
            'entry_time': self.Time,
            'call_strike': best_call.Strike,
            'put_strike': best_put.Strike,
            'expiry': best_call.Expiry,
            'underlying_price': current_price
        }
        
        self.last_trade_time = self.Time
        self.Log(f"SOLD MSFT Strangle: Call ${best_call.Strike} Put ${best_put.Strike} @ ${total_premium:.2f}")
    
    def TradeLongOptions(self, calls, puts):
        """Long options for volatility expansion"""
        current_price = self.Securities[self.msft].Price
        
        if self.market_regime == "BULLISH":
            # Buy calls in bullish low-vol environment
            atm_calls = [c for c in calls if abs(c.Strike - current_price) < current_price * 0.03]
            if atm_calls:
                best_call = min(atm_calls, key=lambda x: x.AskPrice)
                if best_call.AskPrice <= 3.0:  # Reasonable premium limit
                    self.MarketOrder(best_call.Symbol, 1)
                    
                    self.active_positions[best_call.Symbol] = {
                        'type': 'LONG_CALL',
                        'entry_price': best_call.AskPrice,
                        'entry_time': self.Time,
                        'contracts': 1,
                        'strike': best_call.Strike,
                        'expiry': best_call.Expiry,
                        'underlying_price': current_price
                    }
                    
                    self.last_trade_time = self.Time
                    self.Log(f"BOUGHT MSFT Call: ${best_call.Strike} @ ${best_call.AskPrice:.2f}")
                    
        elif self.market_regime == "NEUTRAL":
            # Buy straddles for volatility expansion
            atm_calls = [c for c in calls if abs(c.Strike - current_price) < current_price * 0.02]
            atm_puts = [p for p in puts if abs(p.Strike - current_price) < current_price * 0.02]
            
            if atm_calls and atm_puts:
                best_call = min(atm_calls, key=lambda x: abs(x.Strike - current_price))
                matching_puts = [p for p in atm_puts if p.Expiry == best_call.Expiry and p.Strike == best_call.Strike]
                
                if matching_puts:
                    best_put = matching_puts[0]
                    total_cost = best_call.AskPrice + best_put.AskPrice
                    
                    if total_cost <= 4.0:  # Reasonable cost limit
                        self.MarketOrder(best_call.Symbol, 1)
                        self.MarketOrder(best_put.Symbol, 1)
                        
                        position_id = f"MSFT_STRADDLE_{self.Time.strftime('%Y%m%d_%H%M')}"
                        self.active_positions[position_id] = {
                            'type': 'LONG_STRADDLE',
                            'call_symbol': best_call.Symbol,
                            'put_symbol': best_put.Symbol,
                            'entry_cost': total_cost,
                            'entry_time': self.Time,
                            'strike': best_call.Strike,
                            'expiry': best_call.Expiry,
                            'underlying_price': current_price
                        }
                        
                        self.last_trade_time = self.Time
                        self.Log(f"BOUGHT MSFT Straddle: ${best_call.Strike} @ ${total_cost:.2f}")
    
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
        """Determine if position should be closed"""
        # Days to expiration
        days_to_expiry = (position_info['expiry'].date() - self.Time.date()).days
        
        # Close near expiration
        if days_to_expiry <= 2:
            return True, "EXPIRATION"
        
        # Earnings protection
        if self.msft_earnings_proximity == "NEAR" and position_info['type'] in ['CASH_SECURED_PUT', 'COVERED_CALL', 'SHORT_STRANGLE']:
            return True, "EARNINGS_PROTECTION"
        
        # Strategy-specific exits
        if position_info['type'] in ['CASH_SECURED_PUT', 'COVERED_CALL']:
            return self.ShouldCloseShortOption(position_info, data)
        elif position_info['type'] == 'SHORT_STRANGLE':
            return self.ShouldCloseStrangle(position_info, data)
        elif position_info['type'] in ['LONG_CALL', 'LONG_STRADDLE']:
            return self.ShouldCloseLongPosition(position_info, data)
        
        return False, ""
    
    def ShouldCloseShortOption(self, position_info, data):
        """Close conditions for short single options"""
        symbol_key = None
        for key in ['symbol', 'call_symbol', 'put_symbol']:
            if key in position_info and position_info[key] in data:
                symbol_key = position_info[key]
                break
        
        if symbol_key and symbol_key in data:
            current_price = data[symbol_key].Price
            entry_price = position_info['entry_price']
            
            # Take profit at 55% of max profit
            if current_price <= entry_price * (1 - self.profit_target):
                return True, "PROFIT_TARGET"
            
            # Stop loss at 250% of premium received
            if current_price >= entry_price * self.stop_loss:
                return True, "STOP_LOSS"
            
            # Time-based profit taking
            days_held = (self.Time - position_info['entry_time']).days
            if days_held >= 21 and current_price <= entry_price * 0.7:  # 30% profit after 3 weeks
                return True, "TIME_PROFIT"
        
        return False, ""
    
    def ShouldCloseStrangle(self, position_info, data):
        """Close conditions for strangles"""
        if (position_info['call_symbol'] in data and 
            position_info['put_symbol'] in data):
            call_price = data[position_info['call_symbol']].Price
            put_price = data[position_info['put_symbol']].Price
            
            current_total = call_price + put_price
            entry_premium = position_info['entry_premium']
            
            # Take profit
            if current_total <= entry_premium * (1 - self.profit_target):
                return True, "PROFIT_TARGET"
            
            # Stop loss
            if current_total >= entry_premium * 2.0:  # 200% stop for strangle
                return True, "STOP_LOSS"
        
        return False, ""
    
    def ShouldCloseLongPosition(self, position_info, data):
        """Close conditions for long options"""
        if position_info['type'] == 'LONG_CALL':
            symbol = position_info.get('symbol')
            if symbol and symbol in data:
                current_price = data[symbol].Price
                entry_price = position_info['entry_price']
                
                # Take profit at 100% gain
                if current_price >= entry_price * 2.0:
                    return True, "PROFIT_TARGET"
                
                # Stop loss at 50% of premium paid
                if current_price <= entry_price * 0.5:
                    return True, "STOP_LOSS"
        
        elif position_info['type'] == 'LONG_STRADDLE':
            if (position_info['call_symbol'] in data and 
                position_info['put_symbol'] in data):
                call_price = data[position_info['call_symbol']].Price
                put_price = data[position_info['put_symbol']].Price
                
                current_total = call_price + put_price
                entry_cost = position_info['entry_cost']
                
                # Take profit at 75% gain
                if current_total >= entry_cost * 1.75:
                    return True, "PROFIT_TARGET"
                
                # Stop loss at 50% of premium paid
                if current_total <= entry_cost * 0.5:
                    return True, "STOP_LOSS"
        
        return False, ""
    
    def ClosePosition(self, position_id, position_info, reason):
        """Close option position"""
        try:
            if position_info['type'] == 'SHORT_STRANGLE':
                # Close both legs
                self.MarketOrder(position_info['call_symbol'], 1)
                self.MarketOrder(position_info['put_symbol'], 1)
                self.Log(f"CLOSED MSFT Strangle ({reason})")
                
            elif position_info['type'] == 'LONG_STRADDLE':
                # Sell both legs
                self.MarketOrder(position_info['call_symbol'], -1)
                self.MarketOrder(position_info['put_symbol'], -1)
                self.Log(f"CLOSED MSFT Straddle ({reason})")
                
            elif position_info['type'] in ['CASH_SECURED_PUT', 'COVERED_CALL']:
                # Close single option
                contracts = position_info['contracts']
                symbol = position_id  # For single options, position_id is the symbol
                self.MarketOrder(symbol, contracts)  # Buy back short position
                self.Log(f"CLOSED MSFT {position_info['type']} ({reason})")
                
            elif position_info['type'] == 'LONG_CALL':
                # Sell long option
                symbol = position_id
                self.MarketOrder(symbol, -1)
                self.Log(f"CLOSED MSFT Long Call ({reason})")
                
        except Exception as e:
            self.Log(f"Error closing MSFT position {position_id}: {str(e)}")
    
    def AllIndicatorsReady(self):
        """Check if all indicators are ready"""
        indicators = [
            self.ema_20, self.ema_50, self.sma_200, 
            self.bb, self.rsi, self.atr, self.volume_sma,
            self.tech_momentum
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Log final performance"""
        self.Log(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        algo_performance = (self.Portfolio.TotalPortfolioValue / 6319 - 1) * 100
        self.Log(f"MSFT Options Algorithm Performance: {algo_performance:.2f}%")
        self.Log(f"Active Positions at End: {len(self.active_positions)}")