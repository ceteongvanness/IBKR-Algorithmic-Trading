from AlgorithmImports import *
import pandas as pd
import numpy as np
from datetime import time, timedelta, datetime
from QuantConnect.Brokerages import BrokerageName
from QuantConnect import AccountType

# Custom fee models
class CustomOptionsFeeModel(FeeModel):
    def __init__(self, algorithm, per_contract_fee=0.05):
        super().__init__()
        self.algorithm = algorithm
        self.per_contract_fee = per_contract_fee

    def GetOrderFee(self, parameters):
        # Fee is $0.05 per contract
        contract_fee = self.per_contract_fee * abs(parameters.Order.AbsoluteQuantity)
        total_fee = contract_fee
        return OrderFee(CashAmount(total_fee, "USD"))

# Custom security initializer
class CustomInitializer(BrokerageModelSecurityInitializer):
    def __init__(self, brokerage_model, security_seeder, algorithm):
        super().__init__(brokerage_model, security_seeder)
        self.algorithm = algorithm

    def Initialize(self, security):
        super().Initialize(security)
        if security.Type == SecurityType.Option:
            security.SetFeeModel(CustomOptionsFeeModel(self.algorithm))

class CombinedStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2022, 1, 1)
        self.SetEndDate(2025, 1, 8)
        self.SetCash(100000)
        
        # Set brokerage model to Interactive Brokers for options trading
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)

        # Initialize SPX Options Strategy
        self.InitializeSPXOptionsStrategy()
        
    def InitializeSPXOptionsStrategy(self):
        # Set up SPX options strategy with 100% allocation
        self.options_portfolio_value = self.Portfolio.TotalPortfolioValue
        
        self.spx_index = self.AddIndex("SPX", Resolution.Minute).Symbol
        self.vix = self.AddIndex("VIX", Resolution.Minute).Symbol
        self.daily_sma = self.SMA(self.spx_index, 3, Resolution.Daily)
        self.weekly_sma = self.SMA(self.spx_index, 20, Resolution.Daily)
        
        option = self.AddIndexOption("SPX", "SPXW", Resolution.Minute)
        option.SetFilter(self.OptionFilter)
        self.option_symbol = option.Symbol

        # Strategy parameters
        self.bp_spread = 15
        self.bc_spread = 15
        self.otm_threshold_pct = 0.001

        # Trade windows
        self.bp_trade_window_start = time(13, 30)
        self.bp_trade_window_end = time(15, 30)
        self.bc_trade_window_start = time(15, 0)
        self.bc_trade_window_end = time(15, 30)
        
        # Position management windows
        self.profit_check_start = time(14, 0)
        self.profit_check_end = time(15, 45)
        self.profit_target_pct = 0.25
        self.stop_loss_pct = 0.50
        
        self.market_close = time(16, 0)
        self.last_bp_trade_date = None
        self.last_bc_trade_date = None

        # Track trades and positions
        self.session_trade_count = 0
        self.current_session_date = None
        self.open_positions = {}

        # FOMC blackout dates
        self.fomc_dates = {
            datetime(2022, 5, 4).date(), datetime(2022, 6, 15).date(),
            datetime(2022, 7, 27).date(), datetime(2022, 9, 21).date(),
            datetime(2022, 11, 2).date(), datetime(2022, 12, 14).date(),
            datetime(2023, 2, 1).date(), datetime(2023, 3, 22).date(),
            datetime(2023, 5, 3).date(), datetime(2023, 6, 14).date(),
            datetime(2023, 7, 26).date(), datetime(2023, 9, 20).date(),
            datetime(2023, 11, 1).date(), datetime(2023, 12, 13).date(),
            datetime(2024, 1, 31).date(), datetime(2024, 3, 20).date(),
            datetime(2024, 5, 1).date(), datetime(2024, 6, 12).date(),
            datetime(2024, 7, 31).date(), datetime(2024, 9, 17).date(),
            datetime(2024, 11, 5).date(), datetime(2024, 12, 17).date(),
            datetime(2025, 1, 29).date()
        }
        
        # Set security initializer for options
        seeder = FuncSecuritySeeder(self.GetLastKnownPrices)
        self.SetSecurityInitializer(CustomInitializer(self.BrokerageModel, seeder, self))
        
        self.SetWarmUp(timedelta(days=25))
        
    def OptionFilter(self, universe):
        return universe.IncludeWeeklys() \
                       .Expiration(timedelta(0), timedelta(0)) \
                       .Strikes(-10, 10)

    def IsMarketRegimeFavorable(self):
        """Market regime filter"""
        if not self.weekly_sma.IsReady:
            return False
        
        if self.vix not in self.Securities:
            return False
        
        spx_price = self.Securities[self.spx_index].Price
        vix_value = self.Securities[self.vix].Price
        
        if spx_price == 0 or vix_value == 0:
            return False
        
        # Regime requirements: SPX above 20-day SMA AND VIX < 25
        sma_trend = spx_price > self.weekly_sma.Current.Value
        low_vol = vix_value < 25
        
        favorable = sma_trend and low_vol
        
        if not favorable:
            trend_msg = "above" if sma_trend else "below"
            debug_msg = str(self.Time) + " - Unfavorable regime: SPX " + trend_msg + " 20-day SMA"
            self.Debug(debug_msg)
            self.Debug("VIX at " + str(round(vix_value, 2)))
        
        return favorable

    def CalculateVIXBasedPositionSize(self, spx_price, spread_width):
        """VIX-based position sizing with natural portfolio scaling"""
        if self.vix not in self.Securities:
            return 15
        
        vix_value = self.Securities[self.vix].Price
        if vix_value == 0:
            return 15
        
        # VIX-based base position sizing
        if vix_value < 15:
            base_qty = 20
        elif vix_value < 20:
            base_qty = 15
        elif vix_value < 25:
            base_qty = 10
        else:
            base_qty = 5
        
        # Natural Portfolio Scaling
        current_value = self.Portfolio.TotalPortfolioValue
        portfolio_growth_factor = current_value / 100000
        
        # Apply scaling with caps
        if portfolio_growth_factor <= 1.5:
            scaling_factor = portfolio_growth_factor
        elif portfolio_growth_factor <= 3.0:
            scaling_factor = 1.5 + (portfolio_growth_factor - 1.5) * 0.8
        elif portfolio_growth_factor <= 5.0:
            scaling_factor = 2.7 + (portfolio_growth_factor - 3.0) * 0.5
        else:
            scaling_factor = 3.7 + (portfolio_growth_factor - 5.0) * 0.2
        
        # Calculate final position size
        scaled_qty = int(base_qty * scaling_factor)
        
        # Risk management caps
        max_position = min(100, int(current_value / 3000))
        final_qty = max(5, min(scaled_qty, max_position))
        
        # Debug scaling information once per hour
        if self.Time.minute % 60 == 0:
            debug_msg = "Position Scaling: Portfolio $" + str(int(current_value))
            debug_msg += " (" + str(round(portfolio_growth_factor, 1)) + "x growth), VIX " + str(round(vix_value, 1))
            debug_msg += ", Base " + str(base_qty) + " -> Scaled " + str(final_qty) + " contracts"
            self.Debug(str(self.Time) + " - " + debug_msg)
        
        return final_qty

    def CheckPositionManagement(self, data):
        """Check for both profit taking AND stop losses"""
        current_time = self.Time.time()
        
        # Only check during position management window
        if not (self.profit_check_start <= current_time <= self.profit_check_end):
            return
        
        positions_to_close = []
        
        for symbol, position_info in self.open_positions.items():
            try:
                if symbol not in data:
                    continue
                    
                # Get current option data
                option_data = data[symbol]
                if not option_data or not hasattr(option_data, 'BidPrice') or not hasattr(option_data, 'AskPrice'):
                    continue
                
                # Calculate current P&L
                is_short = position_info["is_short"]
                entry_price = position_info.get("entry_price", 0)
                
                if is_short:
                    # For short positions
                    current_price = option_data.AskPrice
                    if entry_price > 0 and current_price > 0:
                        pnl_pct = (entry_price - current_price) / entry_price
                        
                        # Check profit target
                        if pnl_pct >= self.profit_target_pct:
                            reason = "PROFIT TARGET: " + str(round(pnl_pct*100, 1)) + "%"
                            positions_to_close.append((symbol, reason))
                        # Check stop loss
                        elif pnl_pct <= -self.stop_loss_pct:
                            reason = "STOP LOSS: " + str(round(pnl_pct*100, 1)) + "%"
                            positions_to_close.append((symbol, reason))
                else:
                    # For long positions
                    current_price = option_data.BidPrice
                    if entry_price > 0 and current_price > 0:
                        pnl_pct = (current_price - entry_price) / entry_price
                        
                        # Check profit target
                        if pnl_pct >= self.profit_target_pct:
                            reason = "PROFIT TARGET: " + str(round(pnl_pct*100, 1)) + "%"
                            positions_to_close.append((symbol, reason))
                        # Check stop loss  
                        elif pnl_pct <= -self.stop_loss_pct:
                            reason = "STOP LOSS: " + str(round(pnl_pct*100, 1)) + "%"
                            positions_to_close.append((symbol, reason))
                            
            except Exception as e:
                continue
        
        # Close positions that meet exit criteria
        for symbol, reason in positions_to_close:
            self.ClosePosition(symbol, reason)

    def ClosePosition(self, symbol, reason):
        """Close a position early for profit taking OR stop loss"""
        if symbol not in self.open_positions:
            return
            
        position_info = self.open_positions[symbol]
        quantity = position_info["quantity"]
        
        try:
            # Close the position
            self.MarketOrder(symbol, -quantity)
            
            strategy = position_info["strategy"]
            debug_msg = str(self.Time) + " - POSITION MANAGEMENT: Closed " + strategy + " " + str(symbol)
            self.Debug(debug_msg)
            self.Debug("Qty: " + str(-quantity) + ", Reason: " + reason)
            
        except Exception as e:
            self.Debug("Error closing position " + str(symbol) + ": " + str(e))

    def OnData(self, data):
        if self.IsWarmingUp:
            return
        
        # Check for position management first
        self.CheckPositionManagement(data)
        
        # Then execute normal strategy
        self.ExecuteSPXOptionsStrategy(data)
        
    def ExecuteSPXOptionsStrategy(self, data):
        """Main strategy execution logic"""
        current_date = self.Time.date()
        current_time = self.Time.time()
        spx_price = self.Securities[self.spx_index].Price

        # Skip FOMC dates
        if current_date in self.fomc_dates:
            return

        # Market regime filter
        if not self.IsMarketRegimeFavorable():
            return

        # Reset session date tracking
        if self.current_session_date != current_date:
            self.current_session_date = current_date
            self.session_trade_count = 0
            vix_value = self.Securities[self.vix].Price if self.vix in self.Securities else "N/A"
            sma20_value = self.weekly_sma.Current.Value if self.weekly_sma.IsReady else "N/A"
            debug_msg = str(self.Time) + " - New trading session: SPX " + str(spx_price)
            self.Debug(debug_msg)
            self.Debug("VIX " + str(vix_value) + ", 20-day SMA " + str(sma20_value))

        if spx_price == 0:
            return

        # Try trading strategies
        self.TryBullPutStrategy(data, current_date, current_time, spx_price)
        self.TryBearCallStrategy(data, current_date, current_time, spx_price)

    def TryBullPutStrategy(self, data, current_date, current_time, spx_price):
        """Execute Bull Put Strategy"""
        # Skip if already traded today
        if self.last_bp_trade_date == current_date:
            return

        # Check trade window
        if not (self.bp_trade_window_start < current_time <= self.bp_trade_window_end):
            return

        if not self.daily_sma.IsReady:
            return

        # Entry condition: SPX > SMA
        if spx_price <= self.daily_sma.Current.Value:
            return

        chain = data.OptionChains.get(self.option_symbol, None)
        if not chain:
            return

        # Filter for puts expiring today
        options = [c for c in chain
                   if c.Expiry.date() == current_date and
                   c.Right == OptionRight.Put]

        if len(options) < 2:
            return

        # Sort puts by strike price
        options.sort(key=lambda c: c.Strike, reverse=True)
        
        # Find OTM puts
        otm_puts = [p for p in options if p.Strike < spx_price]
        
        if len(otm_puts) < 2:
            return

        # Select strikes
        short_put = otm_puts[1]
        long_put = next((p for p in options if p.Strike == short_put.Strike - self.bp_spread), None)

        if not long_put or short_put.AskPrice <= 0 or long_put.BidPrice <= 0:
            return

        # Position sizing
        qty = self.CalculateVIXBasedPositionSize(spx_price, self.bp_spread)
        if qty <= 0:
            self.Debug(str(self.Time) + " - Bull Put: No available capital")
            return

        # Execute trades
        self.session_trade_count += 1
        self.MarketOrder(long_put.Symbol, qty)
        self.MarketOrder(short_put.Symbol, -qty)

        # Track positions
        self.open_positions[long_put.Symbol] = {
            "quantity": qty, 
            "strike": long_put.Strike, 
            "is_short": False, 
            "strategy": "BullPut",
            "entry_price": long_put.AskPrice
        }
        self.open_positions[short_put.Symbol] = {
            "quantity": -qty, 
            "strike": short_put.Strike, 
            "is_short": True, 
            "strategy": "BullPut",
            "entry_price": short_put.BidPrice
        }

        # Debug output
        debug_msg = str(self.Time) + " - Bull Put placed: Long " + str(long_put.Strike) + ", Short " + str(short_put.Strike)
        self.Debug(debug_msg)
        sma_val = round(self.daily_sma.Current.Value, 2)
        self.Debug("SPX @ " + str(round(spx_price, 2)) + " > SMA " + str(sma_val) + ", Qty " + str(qty))

        self.last_bp_trade_date = current_date

    def TryBearCallStrategy(self, data, current_date, current_time, spx_price):
        """Execute Bear Call Strategy"""
        # Skip if already traded today
        if self.last_bc_trade_date == current_date:
            return

        # Check trade window
        if not (self.bc_trade_window_start <= current_time <= self.bc_trade_window_end):
            return

        chain = data.OptionChains.get(self.option_symbol, None)
        if not chain:
            return

        # Filter for calls
        opts = [c for c in chain
                if c.Expiry.date() == current_date
                and c.Right == OptionRight.Call
                and c.Strike > spx_price]

        if len(opts) < 10:
            return

        # Sort by strike
        opts.sort(key=lambda c: c.Strike)

        # Find suitable strikes
        threshold_price = spx_price * (1 + self.otm_threshold_pct)
        
        short_call = None
        for opt in opts:
            if opt.Strike > threshold_price:
                short_call = opt
                break
        
        if not short_call:
            return

        long_call = next((p for p in opts if p.Strike == short_call.Strike + self.bc_spread), None)

        if not long_call:
            return

        # Check data availability
        if (short_call.Symbol not in data or
            data[short_call.Symbol] is None or
            data[short_call.Symbol].Ask is None or
            data[short_call.Symbol].Ask.Close <= 0 or
            long_call.Symbol not in data or
            data[long_call.Symbol] is None or
            data[long_call.Symbol].Bid is None or
            data[long_call.Symbol].Bid.Close <= 0):
            return
        
        # Calculate premium
        short_call_bid = data[short_call.Symbol].Bid.Close
        long_call_ask = data[long_call.Symbol].Ask.Close
        net_premium = short_call_bid - long_call_ask
        
        # Check minimum premium
        if net_premium < 0.50:
            return

        # Position sizing
        quantity = self.CalculateVIXBasedPositionSize(spx_price, self.bc_spread)
        if quantity <= 0:
            self.Debug(str(self.Time) + " - Bear Call: No available capital")
            return

        # Execute trades
        self.session_trade_count += 1

        try:
            self.MarketOrder(long_call.Symbol, quantity)
            self.MarketOrder(short_call.Symbol, -quantity)

            # Track positions
            self.open_positions[long_call.Symbol] = {
                "quantity": quantity, 
                "strike": long_call.Strike, 
                "is_short": False, 
                "strategy": "BearCall",
                "entry_price": long_call_ask
            }
            self.open_positions[short_call.Symbol] = {
                "quantity": -quantity, 
                "strike": short_call.Strike, 
                "is_short": True, 
                "strategy": "BearCall",
                "entry_price": short_call_bid
            }

            # Debug output
            otm_percentage = ((short_call.Strike - spx_price) / spx_price) * 100
            debug_msg = str(self.Time) + " - Bear Call placed: Long " + str(long_call.Strike) + ", Short " + str(short_call.Strike)
            self.Debug(debug_msg)
            premium_str = str(int(net_premium*100))
            otm_str = str(round(otm_percentage, 2))
            spx_str = str(round(spx_price, 2))
            self.Debug("(" + otm_str + "% OTM), Qty " + str(quantity) + ", SPX " + spx_str + ", Premium $" + premium_str)
            
            self.last_bc_trade_date = current_date
            
        except Exception as e:
            error_msg = "Error placing Bear Call orders at " + str(self.Time) + ": " + str(e)
            self.Debug(error_msg)
            self.session_trade_count -= 1
            return

    def OnOrderEvent(self, orderEvent):
        # Equity slippage
        if orderEvent.Status == OrderStatus.Filled:
            sec = self.Securities[orderEvent.Symbol]
            if sec.Type == SecurityType.Equity:
                notional = abs(orderEvent.FillPrice * orderEvent.FillQuantity)
                slip = notional * 0.0001
                self.Portfolio.CashBook[sec.QuoteCurrency.Symbol].AddAmount(-slip)
        
        if orderEvent.Status == OrderStatus.Filled:
            symbol = orderEvent.Symbol
            quantity = orderEvent.FillQuantity
            
            # Update positions
            if symbol in self.open_positions:
                if quantity == -self.open_positions[symbol]["quantity"]:
                    # Order closes the position
                    strategy = self.open_positions[symbol]["strategy"]
                    del self.open_positions[symbol]
                    debug_msg = str(self.Time) + " - " + strategy + " position closed: " + str(symbol)
                    self.Debug(debug_msg + ", Qty: " + str(quantity))
                else:
                    # Update quantity
                    self.open_positions[symbol]["quantity"] = quantity
                    debug_msg = str(self.Time) + " - Position updated: " + str(symbol) + ", Qty: " + str(quantity)
                    self.Debug(debug_msg)
            
            # Order fill debug
            order_msg = "Order filled: " + str(orderEvent.Symbol) + ", Qty: " + str(orderEvent.FillQuantity)
            self.Debug(order_msg)
            fee_msg = "Price: " + str(orderEvent.FillPrice) + ", Fee: $" + str(orderEvent.OrderFee.Value.Amount)
            self.Debug(fee_msg)

    def OnEndOfDay(self):
        # Update portfolio values
        options_value = self.Portfolio.TotalPortfolioValue
        self.options_portfolio_value = options_value
        
        # Calculate metrics
        portfolio_growth = (options_value / 100000) - 1
        portfolio_multiple = options_value / 100000
        
        vix_value = self.Securities[self.vix].Price if self.vix in self.Securities else "N/A"
        open_positions_count = len(self.open_positions)
        
        # Debug output
        growth_pct = portfolio_growth * 100
        portfolio_msg = "End of Day - Portfolio: $" + str(int(self.options_portfolio_value))
        self.Debug(portfolio_msg)
        growth_msg = "Growth: " + str(round(growth_pct, 1)) + "% (" + str(round(portfolio_multiple, 1)) + "x)"
        positions_msg = ", VIX: " + str(vix_value) + ", Open: " + str(open_positions_count)
        self.Debug(growth_msg + positions_msg)
        self.Debug("Strategy: Winning + Profit Taking + Stop Loss + Natural Scaling")

    def OnEndOfAlgorithm(self):
        final_value = self.Portfolio.TotalPortfolioValue
        total_return = (final_value - 100000) / 100000 * 100
        portfolio_multiple = final_value / 100000
        
        self.Log("=== NATURAL SCALING STRATEGY RESULTS ===")
        self.Log("Final Portfolio Value: $" + str(round(final_value, 2)))
        self.Log("Total Return: " + str(round(total_return, 2)) + "%")
        self.Log("Portfolio Growth: " + str(round(portfolio_multiple, 1)) + "x original size")
        
        # Position size evolution
        if self.vix in self.Securities:
            vix_value = self.Securities[self.vix].Price
            if 15 <= vix_value < 20:
                final_base_size = 15
                if portfolio_multiple <= 1.5:
                    final_scaled_size = int(final_base_size * portfolio_multiple)
                elif portfolio_multiple <= 3.0:
                    final_scaled_size = int(final_base_size * (1.5 + (portfolio_multiple - 1.5) * 0.8))
                else:
                    final_scaled_size = int(final_base_size * (2.7 + (portfolio_multiple - 3.0) * 0.5))
                
                evolution_msg = "Position Size Evolution: 15 contracts -> " + str(final_scaled_size) + " contracts"
                self.Log(evolution_msg)
                growth_factor = round(final_scaled_size/15, 1)
                self.Log("Position Size Growth: " + str(growth_factor) + "x larger")
        
        self.Log("Strategy Features: Market Regime Filter + VIX Sizing + Profit Taking + Stop Loss + Natural Scaling")
