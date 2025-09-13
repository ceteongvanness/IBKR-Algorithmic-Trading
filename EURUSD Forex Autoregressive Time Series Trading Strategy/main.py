from AlgorithmImports import *
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA

class EURUSDAutoregression(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2018, 1, 1)   
        self.SetEndDate(2024, 12, 31)    
        self.SetCash(100000)             

        # Forex pair
        self.symbol = self.AddForex("EURUSD", Resolution.Daily, Market.Oanda).Symbol

        # Parameters
        self.lookback = 60       # days of history for training
        self.retrain_freq = 30   # retrain every N days
        self.last_train = -self.retrain_freq
        self.model = None
        self.current_forecast = 0
        self.stop_loss_pct = 0.01  # 1% stop loss
        self.take_profit_pct = 0.02  # 2% take profit

        # Schedule daily trade execution after data update
        self.Schedule.On(self.DateRules.EveryDay(self.symbol),
                         self.TimeRules.BeforeMarketClose(self.symbol, 1),
                         self.TradeSignal)

    def OnData(self, data):
        # Not trading directly here, handled by scheduled TradeSignal
        pass

    def TrainModel(self):
        # Get history for AR model
        history = self.History(self.symbol, self.lookback, Resolution.Daily)
        if history.empty: 
            return False
        
        closes = history["close"].values
        returns = np.diff(np.log(closes))  # log returns

        try:
            # Fit ARIMA(p,0,0) ~ AR model
            model = ARIMA(returns, order=(1,0,0))
            self.model = model.fit()
            self.Debug(f"Model retrained on {self.Time.date()}")
            return True
        except Exception as e:
            self.Debug(f"Model training error: {str(e)}")
            return False

    def Forecast(self):
        if self.model is None:
            return 0
        try:
            forecast = self.model.forecast(steps=1)
            return forecast[0]
        except:
            return 0

    def TradeSignal(self):
        # Retrain model every N days
        if (self.Time - self.StartDate).days - self.last_train >= self.retrain_freq:
            if self.TrainModel():
                self.last_train = (self.Time - self.StartDate).days

        # Forecast return
        self.current_forecast = self.Forecast()

        # Generate signal
        if self.current_forecast > 0:
            self.SetHoldings(self.symbol, 0.95)
        elif self.current_forecast < 0:
            self.SetHoldings(self.symbol, -0.95)

        # Add stop loss / take profit
        if self.Portfolio[self.symbol].Invested:
            invested_price = self.Portfolio[self.symbol].AveragePrice
            current_price = self.Securities[self.symbol].Price
            direction = np.sign(self.Portfolio[self.symbol].Quantity)

            stop_loss_level = invested_price * (1 - self.stop_loss_pct * direction)
            take_profit_level = invested_price * (1 + self.take_profit_pct * direction)

            if (direction == 1 and (current_price <= stop_loss_level or current_price >= take_profit_level)) \
               or (direction == -1 and (current_price >= stop_loss_level or current_price <= take_profit_level)):
                self.Liquidate(self.symbol)