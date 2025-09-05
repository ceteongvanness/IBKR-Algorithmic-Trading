from AlgorithmImports import *

class HighWinRateEnsembleStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2021, 1, 1)
        self.SetEndDate(2025, 1, 1)
        self.SetCash(1000)

        self.symbol = self.AddEquity("AAPL", Resolution.Daily).Symbol

        self.fast_sma = self.SMA(self.symbol, 15, Resolution.Daily)
        self.slow_sma = self.SMA(self.symbol, 50, Resolution.Daily)
        self.bb = self.BB(self.symbol, 20, 2, MovingAverageType.Simple, Resolution.Daily)
        self.rsi = self.RSI(self.symbol, 14, MovingAverageType.Wilders, Resolution.Daily)
        self.atr = self.ATR(self.symbol, 14, MovingAverageType.Simple, Resolution.Daily)

        self.SetWarmUp(60)

        self.position_ticket = None
        self.entry_price = 0
        self.stop_price = 0
        self.take_profit_price = 0

    def OnData(self, data):
        if self.IsWarmingUp or not self.bb.IsReady or not self.fast_sma.IsReady or not self.slow_sma.IsReady:
            return

        price = self.Securities[self.symbol].Price

        # Debug info
        self.Debug(
            f"Price: {price:.2f}, Fast SMA: {self.fast_sma.Current.Value:.2f}, "
            f"Slow SMA: {self.slow_sma.Current.Value:.2f}, BB Lower: {self.bb.LowerBand.Current.Value:.2f}, "
            f"RSI: {self.rsi.Current.Value:.2f}, ATR %: {(self.atr.Current.Value / price) * 100:.2f}%"
        )

        if not self.Portfolio.Invested:
            # Entry conditions tightened
            if (self.fast_sma.Current.Value > self.slow_sma.Current.Value and
                price < self.bb.LowerBand.Current.Value * 0.99 and  # Slightly below lower Bollinger Band
                self.rsi.Current.Value < 30 and                   # Strong oversold
                self.atr.Current.Value / price < 0.02):          # Volatility filter

                quantity = int(self.Portfolio.Cash / price)
                if quantity > 0:
                    self.position_ticket = self.MarketOrder(self.symbol, quantity)
                    self.entry_price = price
                    self.stop_price = price * 0.995   # 0.5% stop loss
                    self.take_profit_price = price * 1.015  # 1.5% take profit

                    self.Debug(f"Entered at {price}, stop: {self.stop_price:.2f}, target: {self.take_profit_price:.2f}")

        else:
            # Trailing stop adjustment during position
            current_price = self.Securities[self.symbol].Price

            # Move stop price up if price rose favorably by 1%
            if current_price > self.entry_price * 1.01:
                new_stop = current_price * 0.995
                if new_stop > self.stop_price:
                    self.stop_price = new_stop
                    self.Debug(f"Trailing stop moved up to {self.stop_price:.2f}")

            # Check stop loss or take profit exit
            if current_price <= self.stop_price or current_price >= self.take_profit_price:
                self.Debug(f"Exiting position at {current_price:.2f} (stop: {self.stop_price:.2f}, target: {self.take_profit_price:.2f})")
                self.Liquidate()
                self.position_ticket = None