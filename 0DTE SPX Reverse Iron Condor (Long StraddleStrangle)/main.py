from AlgorithmImports import *

class ZeroDTE_SPX_ReverseIronCondor(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2022, 5, 16)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(10000)

        # Add SPX Index
        self.spx = self.AddIndex("SPX", Resolution.Minute).Symbol

        # Add SPX Options
        self.option = self.AddIndexOption("SPX", Resolution.Minute)
        self.option.SetFilter(lambda universe: universe.IncludeWeeklys().Expiration(0, 1).Strikes(-10, 10))

        # Check for trades multiple times per day
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.At(9, 35), self.TradeOptions)
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.At(10, 30), self.TradeOptions)
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.At(14, 30), self.TradeOptions)

        # Strategy Parameters
        self.max_alloc = 0.20  # 20% portfolio allocation
        self.stop_loss_pct = 0.5  # 50% stop loss
        self.profit_take_pct = 0.50  # 50% profit target (since we're betting on big moves)
        self.contracts_per_trade = 1  # Maximum contracts per trade

        # Set Commission Structure
        self.SetSecurityInitializer(lambda security: security.SetFeeModel(CustomFeeModel()))

    def TradeOptions(self):
        # Check if there are existing open SPX option positions
        open_positions = [
            kvp.Value for kvp in self.Portfolio if kvp.Value.Invested and kvp.Key.SecurityType == SecurityType.Option
        ]
        
        if open_positions:
            self.Debug("Existing open SPX option positions detected. Skipping new entry.")
            return  # Skip new trades if there are existing open positions

        if self.Portfolio.TotalPortfolioValue * self.max_alloc < 500:
            self.Debug("Insufficient buying power for new positions.")
            return

        # Get Option Chain Data
        option_chain = self.CurrentSlice.OptionChains.get(self.option.Symbol, None)
        if option_chain is None:
            self.Debug(f"No option chain data available at {self.Time}.")
            return

        # Select ATM Put & Call Contracts
        atm_puts = sorted(
            [contract for contract in option_chain if contract.Right == OptionRight.Put and contract.Greeks.Delta > -0.40],
            key=lambda x: abs(x.Greeks.Delta + 0.30)
        )

        atm_calls = sorted(
            [contract for contract in option_chain if contract.Right == OptionRight.Call and contract.Greeks.Delta < 0.40],
            key=lambda x: abs(x.Greeks.Delta - 0.30)
        )

        if not atm_puts or not atm_calls:
            self.Debug("No suitable ATM puts or calls found.")
            return

        # Select Long Put and Short Put (10 strikes apart)
        long_put = atm_puts[0]
        short_put = next((put for put in atm_puts if put.Strike == long_put.Strike - 10), None)

        # Select Long Call and Short Call (10 strikes apart)
        long_call = atm_calls[0]
        short_call = next((call for call in atm_calls if call.Strike == long_call.Strike + 10), None)

        if not short_put or not short_call:
            self.Debug("No valid short put or short call contract found 10 strikes apart.")
            return

        # Ensure Bid Prices are Not Zero
        if long_put.AskPrice <= 0 or long_call.AskPrice <= 0:
            self.Debug("Ask price is zero for selected contracts.")
            return

        # Calculate max possible contracts based on available allocation
        available_funds = self.Portfolio.TotalPortfolioValue * self.max_alloc  # 20% of portfolio
        max_contracts = int(available_funds / ((long_put.AskPrice + long_call.AskPrice) * 100))  # Ensure contract fits in allocation

        # Limit to 1 contract per trade
        quantity = min(max_contracts, 1)

        if quantity <= 0:
            self.Debug("Insufficient funds for even 1 contract.")
            return

        # Place Orders: Open Inverted Iron Condor (Buy ATM Put, Sell Lower Strike Put, Buy ATM Call, Sell Higher Strike Call)
        self.MarketOrder(long_put.Symbol, quantity)
        self.MarketOrder(short_put.Symbol, -quantity)
        self.MarketOrder(long_call.Symbol, quantity)
        self.MarketOrder(short_call.Symbol, -quantity)

        # Set Profit-Taking and Stop-Loss Orders
        self.LimitOrder(long_put.Symbol, quantity, long_put.AskPrice * (1 + self.profit_take_pct))
        self.StopMarketOrder(long_put.Symbol, quantity, long_put.AskPrice * (1 - self.stop_loss_pct))

        self.LimitOrder(long_call.Symbol, quantity, long_call.AskPrice * (1 + self.profit_take_pct))
        self.StopMarketOrder(long_call.Symbol, quantity, long_call.AskPrice * (1 - self.stop_loss_pct))

        self.Debug(f"Placed orders for {quantity} contracts of SPX 0DTE Inverted Iron Condor.")

    def OnData(self, slice):
        pass  # Not needed for this strategy

    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled:
            self.Debug(f"Order filled: {orderEvent.Symbol}, Quantity: {orderEvent.FillQuantity}")

class CustomFeeModel(FeeModel):
    def GetOrderFee(self, parameters):
        # Define a commission of $1.90 per contract per leg (4 legs in an Iron Condor)
        fee = 1.90 * abs(parameters.Order.Quantity)
        return OrderFee(CashAmount(fee, "USD"))
