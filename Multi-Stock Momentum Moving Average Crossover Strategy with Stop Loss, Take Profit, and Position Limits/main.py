from AlgorithmImports import *

class EnhancedMomentumStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2015, 9, 5)
        self.SetEndDate(2025, 9, 5)
        self.SetCash(1000)

        tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "FB"]
        self.symbols = [self.AddEquity(ticker, Resolution.Daily).Symbol for ticker in tickers]

        self.sma_fast = {symbol: self.SMA(symbol, 20, Resolution.Daily) for symbol in self.symbols}
        self.sma_slow = {symbol: self.SMA(symbol, 60, Resolution.Daily) for symbol in self.symbols}

        self.SetWarmUp(60)

        self.stop_loss_pct = 0.02    # Initial stop-loss at 2%
        self.trailing_start_pct = 0.02  # Start trailing after 2% gain
        self.trailing_stop_pct = 0.01   # Trailing stop 1%
        self.take_profit_pct = 0.05  # Take profit at 5%

        self.entry_prices = {}
        self.max_positions = 3

    def OnData(self, data):
        invested_count = sum(1 for sym in self.symbols if self.Portfolio[sym].Invested)

        for symbol in self.symbols:
            if not self.sma_fast[symbol].IsReady or not self.sma_slow[symbol].IsReady:
                continue

            holdings = self.Portfolio[symbol].Quantity
            price = self.Securities[symbol].Price

            if holdings <= 0:
                # Only enter if we have capacity
                if invested_count >= self.max_positions:
                    continue

                if self.sma_fast[symbol].Current.Value > self.sma_slow[symbol].Current.Value:
                    quantity = int(self.Portfolio.Cash / (price * (self.max_positions - invested_count)))
                    if quantity > 0:
                        self.MarketOrder(symbol, quantity)
                        self.entry_prices[symbol] = price
                        invested_count += 1
                        self.Debug(f"BUY {symbol} {quantity} at {price:.2f}")

            else:
                entry_price = self.entry_prices.get(symbol, price)
                gain = (price - entry_price) / entry_price

                # Stop loss price (initial)
                stop_loss_price = entry_price * (1 - self.stop_loss_pct)

                # Trailing stop logic starts after trailing_start_pct gain
                if gain > self.trailing_start_pct:
                    trail_stop = price * (1 - self.trailing_stop_pct)
                    stop_loss_price = max(stop_loss_price, trail_stop)

                # Sell signals
                if price <= stop_loss_price:
                    self.Debug(f"STOP LOSS hit for {symbol} at {price:.2f}, selling")
                    self.Liquidate(symbol)
                    self.entry_prices.pop(symbol, None)
                elif gain >= self.take_profit_pct:
                    self.Debug(f"TAKE PROFIT hit for {symbol} at {price:.2f}, selling")
                    self.Liquidate(symbol)
                    self.entry_prices.pop(symbol, None)
                elif self.sma_fast[symbol].Current.Value < self.sma_slow[symbol].Current.Value:
                    self.Debug(f"SMA CROSS exit for {symbol} at {price:.2f}, selling")
                    self.Liquidate(symbol)
                    self.entry_prices.pop(symbol, None)
