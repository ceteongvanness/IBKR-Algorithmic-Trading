from AlgorithmImports import *
import statsmodels.api as sm
import numpy as np

class USOAutoregressionOptimization(QCAlgorithm):

    def Initialize(self):
        # Set backtest period and cash
        self.SetStartDate(2015, 1, 1)
        self.SetEndDate(2025, 7, 30)
        self.SetCash(100000)

        # Brokerage & account type
        self.SetBrokerageModel(BrokerageName.Default, AccountType.Margin)

        # Add USO ETF
        self.symbol = self.AddEquity("USO", Resolution.Daily).Symbol

        # Warm up for regression
        self.lookback = int(self.GetParameter("lookback") or 30)

        # Rolling window for AR model
        self.window = RollingWindow[float](self.lookback + 1)

        # Consolidate daily bars into weekly bars
        consolidator = TradeBarConsolidator(timedelta(days=14))
        consolidator.DataConsolidated += self.OnWeeklyBar
        self.SubscriptionManager.AddConsolidator(self.symbol, consolidator)

        # Track signals
        self.predicted_return = 0

        # Risk management parameters
        self.stopLossPct = 0.05
        self.takeProfitPct = 0.10

    def OnWeeklyBar(self, sender, bar):
        # Store weekly close in window
        self.window.Add(float(bar.Close))

        # Run AR(1) regression if enough data
        if self.window.Count > self.lookback:
            try:
                data = np.array([x for x in self.window])
                returns = np.diff(np.log(data))  # log returns
                model = sm.tsa.ARIMA(returns, order=(1,0,0)).fit()
                forecast = model.forecast()[0]
                self.predicted_return = forecast
            except Exception as e:
                self.Debug(f"AR model error: {e}")

    def OnData(self, data: Slice):
        if self.window.Count <= self.lookback:
            return

        invested = self.Portfolio[self.symbol].Invested

        # Trading logic: Long if predicted > 0, Short if < 0
        if self.predicted_return > 0 and not invested:
            self.SetHoldings(self.symbol, 0.5)  # risk control, use 50% allocation
            self.entryPrice = self.Securities[self.symbol].Price
        elif self.predicted_return < 0 and not invested:
            self.SetHoldings(self.symbol, -0.5)
            self.entryPrice = self.Securities[self.symbol].Price
        elif invested:
            price = self.Securities[self.symbol].Price
            pnlPct = (price - self.entryPrice) / self.entryPrice if self.Portfolio[self.symbol].IsLong else (self.entryPrice - price) / self.entryPrice

            # Exit on stop loss or take profit
            if pnlPct <= -self.stopLossPct or pnlPct >= self.takeProfitPct:
                self.Liquidate(self.symbol)

            # Exit if signal flips
            elif (self.predicted_return < 0 and self.Portfolio[self.symbol].IsLong) or \
                 (self.predicted_return > 0 and self.Portfolio[self.symbol].IsShort):
                self.Liquidate(self.symbol)

    def OnEndOfDay(self):
        # Log portfolio value (avoid reserved 'Equity' series)
        self.Plot("Custom Strategy Equity", "PortfolioValue", self.Portfolio.TotalPortfolioValue)
