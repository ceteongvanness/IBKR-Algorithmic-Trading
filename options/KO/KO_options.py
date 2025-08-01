from AlgorithmImports import *
import numpy as np
from datetime import timedelta

class HighWinRateKOOptionsAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set start and end dates
        self.SetStartDate(2022, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash
        self.SetCash(100000)
        
        # Add KO equity
        self.ko = self.AddEquity("KO", Resolution.Minute).Symbol
        
        # Add KO options
        option = self.AddOption("KO", Resolution.Minute)
        self.ko_option = option.Symbol
        
        # Set option filter for dividend stock
        option.SetFilter(self.OptionFilter)
        
        # Set benchmark
        self.SetBenchmark(self.ko)
        
        # Initialize indicators for underlying
        self.Setup_Indicators()
        
        # Options strategy parameters (adjusted for low-volatility dividend stock)
        self.max_dte = 60          # Longer expiration for dividend stock
        self.min_dte = 10          # Minimum days to expiration
        self.target_delta_low = 0.20   # Conservative delta for shorts
        self.target_delta_high = 0.35  # Maximum delta for shorts
        self.profit_target = 0.60      # Take profit at 60% (higher for low vol)
        self.stop_loss = 3.0           # Stop loss at 300% (wider for dividend stock)
        
        # Position tracking
        self.active_positions = {}
        self.last_trade_time = datetime.min
        self.min_trade_interval = timedelta(hours=4)  # Longer interval for KO
        
        # Market and dividend awareness
        self.market_regime = "NEUTRAL"
        self.volatility_regime = "LOW"
        self.dividend_calendar = self.InitializeDividendCalendar()
        
        # Schedule functions
        self.Schedule.On(self.DateRules.EveryDay(self.ko), 
                        self.TimeRules.AfterMarketOpen(self.ko, 30), 
                        self.DailyAnalysis)
        
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday), 
                        self.TimeRules.AfterMarketOpen(self.ko, 60), 
                        self.WeeklyDividendCheck)
        
        # Warm up period
        self.SetWarmUp(100)
        
    def Setup_Indicators(self):
        """Initialize technical indicators for KO"""
        # Trend indicators (longer periods for dividend stock)
        self.ema_20 = self.EMA(self.ko, 20, Resolution.Daily)
        self.ema_50 = self.EMA(self.ko, 50, Resolution.Daily)
        self.sma_200 = self.SMA(self.ko, 200, Resolution.Daily)
        
        # Volatility indicators
        self.bb = self.BB(self.ko, 20, 1.5, Resolution.Daily)  # Tighter bands for low vol stock
        self.atr = self.ATR(self.ko, 21, Resolution.Daily)     # Longer period
        
        # Momentum indicators
        self.rsi = self.RSI(self.ko, 21, Resolution.Daily)     # Longer period for smoother signals
        
        # Volume
        self.volume_sma = self.SMA(self.ko, 30, Resolution.Daily, Field.Volume)
        
        # Dividend yield proxy (price-based)
        self.dividend_yield_proxy = RollingWindow[float](252)  # 1 year of daily returns
        
        # Consumer staples sector strength
        self.sector_momentum = self.RSI(self.ko, 50, Resolution.Weekly)
        
    def InitializeDividendCalendar(self):
        """Initialize approximate dividend calendar for KO"""
        # KO typically declares quarterly dividends
        # Approximate months: March, June, September, December
        return {
            'declaration_months': [3, 6, 9, 12],
            'ex_dividend_offset': 14,  # Days after declaration
            'payment_offset': 30       # Days after ex-dividend
        }
    
    def OptionFilter(self, universe):
        """Filter options for dividend stock strategy"""
        return universe.IncludeWeeklys().Strikes(-8, 8).Expiration(timedelta(7), timedelta(90))
    
    def DailyAnalysis(self):
        """Daily market analysis for KO"""
        if not self.AllIndicatorsReady():
            return
            
        self.AnalyzeMarketRegime()
        self.AnalyzeVolatilityRegime()
        self.UpdateDividendYieldProxy()
    
    def AnalyzeMarketRegime(self):
        """Conservative market regime analysis for dividend stock"""
        current_price = self.Securities[self.ko].Price
        ema_20_value = self.ema_20.Current.Value
        ema_50_value = self.ema_50.Current.Value
        sma_200_value = self.sma_200.Current.Value
        rsi_value = self.rsi.Current.Value
        
        bullish_signals = 0
        bearish_signals = 0
        
        # Long-term trend (critical for dividend stocks)
        if current_price > sma_200_value * 1.02:
            bullish_signals += 3
        elif current_price < sma_200_value * 0.98:
            bearish_signals += 3
            
        # Medium-term trend
        if current_price > ema_50_value and ema_20_value > ema_50_value:
            bullish_signals += 2
        elif current_price < ema_50_value and ema_20_value < ema_50_value:
            bearish_signals += 2
            
        # Momentum (less weight for dividend stock)
        if rsi_value > 55:
            bullish_signals += 1
        elif rsi_value < 45:
            bearish_signals += 1
            
        # Set regime (more conservative thresholds)
        if bullish_signals >= 4 and bullish_signals > bearish_signals + 1:
            self.market_regime = "BULLISH"
        elif bearish_signals >= 4 and bearish_signals > bullish_signals + 1:
            self.market_regime = "BEARISH"
        else:
            self.market_regime = "NEUTRAL"
    
    def AnalyzeVolatilityRegime(self):
        """Analyze volatility for low-volatility dividend stock"""
        bb_width = (self.bb.UpperBand.Current.Value - self.bb.LowerBand.Current.Value) / self.bb.MiddleBand.Current.Value
        
        # Adjusted thresholds for KO's typically low volatility
        if bb_width > 0.06:
            self.volatility_regime = "HIGH"
        elif bb_width < 0.025:
            self.volatility_regime = "VERY_LOW"
        else:
            self.volatility_regime = "LOW"
    
    def UpdateDividendYieldProxy(self):
        """Update dividend yield proxy calculation"""
        if self.ko in self.Securities:
            price = self.Securities[self.ko].Price
            if price > 0:
                # Simple price-based proxy for dividend attractiveness
                self.dividend_yield_proxy.Add(1.0 / price)  # Inverse price as yield proxy
    
    def WeeklyDividendCheck(self):
        """Weekly check for upcoming dividends"""
        current_month = self.Time.month
        current_day = self.Time.day
        
        # Check if we're approaching dividend declaration
        for decl_month in self.dividend_calendar['declaration_months']:
            if current_month == decl_month and 10 <= current_day <= 20:
                self.Log(f"Approaching dividend period for KO in month {current_month}")
                break
    
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        # Manage existing positions first
        self.ManageExistingPositions(data)
        
        # Look for new trading opportunities
        if self.CanTrade() and self.AllIndicatorsReady():
            self.LookForTrades(data)
    
    def CanTrade(self):
        """Enhanced trade filtering for dividend stock"""
        # Standard trading rules
        if self.Time - self.last_trade_time < self.min_trade_interval:
            return False
            
        if len(self.active_positions) >= 2:  # Conservative position limit
            return False
            
        if self.Time.hour < 10 or (self.Time.hour >= 15 and self.Time.minute >= 30):
            return False
        
        # Dividend-specific rules
        if self.IsInDividendBlackoutPeriod():
            return False
            
        return True
    
    def IsInDividendBlackoutPeriod(self):
        """Check if we're in dividend blackout period"""
        current_month = self.Time.month
        current_day = self.Time.day
        
        # Avoid trading 1 week before/after dividend periods
        for decl_month in self.dividend_calendar['declaration_months']:
            # Blackout period around dividend declaration
            if current_month == decl_month and 5 <= current_day <= 30:
                return True
        
        return False
    
    def LookForTrades(self, data):
        """Look for dividend-stock appropriate options trades"""
        chain = data.OptionChains.get(self.ko_option)
        if not chain:
            return
            
        calls, puts = self.FilterOptionsChain(chain)
        
        # Strategy selection based on KO characteristics
        if self.market_regime == "BULLISH" and self.volatility_regime in ["LOW", "HIGH"]:
            # Primary strategy: Cash-secured puts (income generation)
            self.TradeCashSecuredPuts(puts)
            
        elif self.market_regime == "NEUTRAL" and self.volatility_regime == "HIGH":
            # Secondary: Covered calls (if we own stock) or short strangles
            if self.Portfolio[self.ko].Quantity >= 100:
                self.TradeCoveredCalls(calls)
            else:
                self.TradeShortStrangles(calls, puts)
                
        elif self.market_regime == "BEARISH" and self.Portfolio[self.ko].Quantity >= 100:
            # Defensive: Covered calls on existing holdings
            self.TradeCoveredCalls(calls)
            
        elif self.volatility_regime == "VERY_LOW":
            # Volatility expansion play
            self.TradeLongStraddles(calls, puts)
    
    def FilterOptionsChain(self, chain):
        """Filter options chain for KO characteristics"""
        calls = []
        puts = []
        
        current_price = self.Securities[self.ko].Price
        
        for contract in chain:
            # Days to expiration
            days_to_expiry = (contract.Expiry.date() - self.Time.date()).days
            if days_to_expiry < self.min_dte or days_to_expiry > self.max_dte:
                continue
                
            # Basic liquidity check
            if contract.BidPrice <= 0 or contract.AskPrice <= 0:
                continue
                
            # Wider bid-ask spread tolerance for lower-volume stock
            if contract.AskPrice > 0 and (contract.AskPrice - contract.BidPrice) / contract.AskPrice > 0.15:
                continue
                
            # Delta filtering for short premium strategies
            if abs(contract.Greeks.Delta) < 0.15 or abs(contract.Greeks.Delta) > 0.45:
                continue
                
            # Minimum premium for covered calls/cash-secured puts
            if contract.BidPrice < 0.15:  # Lower minimum for KO
                continue
                
            if contract.Right == OptionRight.Call:
                calls.append(contract)
            else:
                puts.append(contract)
        
        return calls, puts
    
    def TradeCashSecuredPuts(self, puts):
        """Primary strategy: Cash-secured puts for income"""
        current_price = self.Securities[self.ko].Price
        
        # Find puts with target delta (conservative)
        target_puts = [p for p in puts 
                      if self.target_delta_low <= abs(p.Greeks.Delta) <= self.target_delta_high 
                      and p.Strike < current_price * 0.97]  # Well out of money
        
        if not target_puts:
            return
            
        # Select put with best yield relative to strike
        best_put = max(target_puts, key=lambda x: x.BidPrice / x.Strike)
        
        # Calculate position size (conservative for dividend stock)
        cash_required = best_put.Strike * 100
        max_contracts = int(self.Portfolio.Cash * 0.4 / cash_required)  # Use max 40% of cash
        
        if max_contracts >= 1:
            contracts_to_sell = min(max_contracts, 1)  # Conservative: 1 contract at a time
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
            self.Log(f"SOLD {contracts_to_sell} KO Cash-Secured Put: ${best_put.Strike} @ ${best_put.BidPrice:.2f}")
    
    def TradeCoveredCalls(self, calls):
        """Covered calls strategy for dividend stock"""
        if self.Portfolio[self.ko].Quantity < 100:
            return
            
        current_price = self.Securities[self.ko].Price
        
        # Find calls with conservative delta (don't want stock called away easily)
        target_calls = [c for c in calls 
                       if self.target_delta_low <= c.Greeks.Delta <= 0.30  # Lower delta for dividend stock
                       and c.Strike > current_price * 1.03]  # Well out of money
        
        if not target_calls:
            return
            
        # Select call with best premium yield
        best_call = max(target_calls, key=lambda x: x.BidPrice)
        
        # Calculate contracts (only cover what we own)
        shares_owned = self.Portfolio[self.ko].Quantity
        max_contracts = int(shares_owned / 100)
        
        if max_contracts >= 1:
            contracts_to_sell = min(max_contracts, 1)  # Conservative approach
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
            self.Log(f"SOLD {contracts_to_sell} KO Covered Call: ${best_call.Strike} @ ${best_call.BidPrice:.2f}")
    
    def TradeShortStrangles(self, calls, puts):
        """Conservative short strangles for neutral markets"""
        current_price = self.Securities[self.ko].Current.Price
        
        # Find conservative strikes
        target_calls = [c for c in calls if 0.20 <= c.Greeks.Delta <= 0.30]
        target_puts = [p for p in puts if -0.30 <= p.Greeks.Delta <= -0.20]
        
        if not target_calls or not target_puts:
            return
            
        # Select equidistant strikes
        best_call = min(target_calls, key=lambda x: abs(x.Strike - current_price * 1.08))
        best_put = min(target_puts, key=lambda x: abs(x.Strike - current_price * 0.92))
        
        # Ensure same expiration
        if best_call.Expiry != best_put.Expiry:
            return
            
        # Check minimum premium
        total_premium = best_call.BidPrice + best_put.BidPrice
        if total_premium < 0.75:  # Lower minimum for KO
            return
            
        # Execute strangle
        self.MarketOrder(best_call.Symbol, -1)
        self.MarketOrder(best_put.Symbol, -1)
        
        # Track position
        position_id = f"KO_STRANGLE_{self.Time.strftime('%Y%m%d_%H%M')}"
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
        self.Log(f"SOLD KO Strangle: Call ${best_call.Strike} Put ${best_put.Strike} @ ${total_premium:.2f}")
    
    def TradeLongStraddles(self, calls, puts):
        """Long straddles for volatility expansion"""
        current_price = self.Securities[self.ko].Price
        
        # Find ATM options
        atm_calls = [c for c in calls if abs(c.Strike - current_price) < current_price * 0.03]
        atm_puts = [p for p in puts if abs(p.Strike - current_price) < current_price * 0.03]
        
        if not atm_calls or not atm_puts:
            return
            
        # Select closest to ATM with same expiration
        best_call = min(atm_calls, key=lambda x: abs(x.Strike - current_price))
        matching_puts = [p for p in atm_puts if p.Expiry == best_call.Expiry and p.Strike == best_call.Strike]
        
        if not matching_puts:
            return
            
        best_put = matching_puts[0]
        total_cost = best_call.AskPrice + best_put.AskPrice
        
        # Only trade if reasonable cost
        if total_cost > current_price * 0.08:  # Max 8% of stock price
            return
            
        # Execute straddle
        self.MarketOrder(best_call.Symbol, 1)
        self.MarketOrder(best_put.Symbol, 1)
        
        # Track position
        position_id = f"KO_STRADDLE_{self.Time.strftime('%Y%m%d_%H%M')}"
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
        self.Log(f"BOUGHT KO Straddle: ${best_call.Strike} @ ${total_cost:.2f}")
    
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
        if days_to_expiry <= 3:
            return True, "EXPIRATION"
        
        # Dividend risk for short positions
        if position_info['type'] in ['CASH_SECURED_PUT', 'COVERED_CALL', 'SHORT_STRANGLE']:
            if self.IsNearExDividend():
                return True, "DIVIDEND_RISK"
        
        # Strategy-specific exits
        if position_info['type'] in ['CASH_SECURED_PUT', 'COVERED_CALL']:
            return self.ShouldCloseShortOption(position_info, data)
        elif position_info['type'] == 'SHORT_STRANGLE':
            return self.ShouldCloseStrangle(position_info, data)
        elif position_info['type'] in ['LONG_STRADDLE']:
            return self.ShouldCloseLongPosition(position_info, data)
        
        return False, ""
    
    def ShouldCloseShortOption(self, position_info, data):
        """Close conditions for short single options"""
        # Get current option price if available
        symbol_key = None
        for key in ['symbol', 'call_symbol', 'put_symbol']:
            if key in position_info:
                symbol_key = position_info[key]
                break
        
        if symbol_key and symbol_key in data and data[symbol_key]:
            current_price = data[symbol_key].Price
            entry_price = position_info['entry_price']
            
            # Take profit at 60% of max profit
            if current_price <= entry_price * (1 - self.profit_target):
                return True, "PROFIT_TARGET"
            
            # Stop loss at 300% of premium received (wider for KO)
            if current_price >= entry_price * self.stop_loss:
                return True, "STOP_LOSS"
            
            # Time-based profit taking (30 days or 75% of time)
            days_held = (self.Time - position_info['entry_time']).days
            days_to_expiry = (position_info['expiry'].date() - self.Time.date()).days
            
            if days_held >= 30 or days_to_expiry <= 7:
                if current_price <= entry_price * 0.7:  # 30% profit
                    return True, "TIME_PROFIT"
        
        return False, ""
    
    def ShouldCloseStrangle(self, position_info, data):
        """Close conditions for strangles"""
        # Check both legs if available
        call_price = put_price = None
        
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
            if current_total >= entry_premium * 2.5:  # 250% stop for strangle
                return True, "STOP_LOSS"
        
        return False, ""
    
    def ShouldCloseLongPosition(self, position_info, data):
        """Close conditions for long options"""
        if (position_info['call_symbol'] in data and 
            position_info['put_symbol'] in data):
            call_price = data[position_info['call_symbol']].Price
            put_price = data[position_info['put_symbol']].Price
            
            current_total = call_price + put_price
            entry_cost = position_info['entry_cost']
            
            # Take profit at 100% gain
            if current_total >= entry_cost * 2.0:
                return True, "PROFIT_TARGET"
            
            # Stop loss at 50% of premium paid
            if current_total <= entry_cost * 0.5:
                return True, "STOP_LOSS"
        
        return False, ""
    
    def IsNearExDividend(self):
        """Enhanced dividend detection"""
        current_month = self.Time.month
        current_day = self.Time.day
        
        # KO typical ex-dividend periods (simplified)
        ex_div_periods = [
            (3, 15, 25),   # March
            (6, 15, 25),   # June
            (9, 15, 25),   # September
            (12, 15, 25)   # December
        ]
        
        for month, start_day, end_day in ex_div_periods:
            if current_month == month and start_day - 5 <= current_day <= end_day + 5:
                return True
        
        return False
    
    def ClosePosition(self, position_id, position_info, reason):
        """Close option position"""
        try:
            if position_info['type'] == 'SHORT_STRANGLE':
                # Close both legs
                self.MarketOrder(position_info['call_symbol'], 1)
                self.MarketOrder(position_info['put_symbol'], 1)
                self.Log(f"CLOSED KO Strangle ({reason})")
                
            elif position_info['type'] == 'LONG_STRADDLE':
                # Sell both legs
                self.MarketOrder(position_info['call_symbol'], -1)
                self.MarketOrder(position_info['put_symbol'], -1)
                self.Log(f"CLOSED KO Straddle ({reason})")
                
            elif position_info['type'] in ['CASH_SECURED_PUT', 'COVERED_CALL']:
                # Close single option
                contracts = position_info['contracts']
                # Find the symbol
                symbol = None
                for key in position_info:
                    if 'symbol' in key.lower() and position_info[key] != position_id:
                        symbol = position_info[key]
                        break
                
                if symbol:
                    self.MarketOrder(symbol, contracts)  # Buy back short position
                    self.Log(f"CLOSED KO {position_info['type']} ({reason})")
                    
        except Exception as e:
            self.Log(f"Error closing KO position {position_id}: {str(e)}")
    
    def AllIndicatorsReady(self):
        """Check if all indicators are ready"""
        indicators = [
            self.ema_20, self.ema_50, self.sma_200, 
            self.bb, self.rsi, self.atr, self.volume_sma,
            self.sector_momentum
        ]
        return all(indicator.IsReady for indicator in indicators)
    
    def OnEndOfAlgorithm(self):
        """Log final performance"""
        self.Log(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        algo_performance = (self.Portfolio.TotalPortfolioValue / 100000 - 1) * 100
        self.Log(f"KO Options Algorithm Performance: {algo_performance:.2f}%")
        self.Log(f"Active Positions at End: {len(self.active_positions)}")