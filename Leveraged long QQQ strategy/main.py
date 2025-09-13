from AlgorithmImports import *

class QQQ_Hourly_MACD_ShortSQQQ(QCAlgorithm):

    def Initialize(self):
        # Backtest span & capital
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2025, 8, 15)
        self.SetCash(100000)

        # Use Interactive Brokers brokerage/fees (do this BEFORE adding securities)
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)

        # Add symbols (hourly regular hours)
        self.qqq  = self.AddEquity("QQQ",  Resolution.Hour).Symbol   # signal source
        self.sqqq = self.AddEquity("SQQQ", Resolution.Hour).Symbol   # instrument we short

        # Indicator setup (fast–slow EMA on QQQ)
        self.fast_period = 8
        self.slow_period = 55
        self.trailing_stop_pct = 0.05  # for short: exit if price rises this much from the post-entry low

        self.fast = self.EMA(self.qqq, self.fast_period, Resolution.Hour)
        self.slow = self.EMA(self.qqq, self.slow_period, Resolution.Hour)

        # Trade state
        self.in_position = False
        self.entry_price = None
        self.trail_min_price = None   # lowest SQQQ price since entry (for trailing stop on a short)
        self.trade_count = 0

        self.prev_fast = None
        self.prev_slow = None

        # Warm up ~3 trading days (covers 62h EMA)
        self.SetWarmUp(timedelta(days=3))

    def OnData(self, data: Slice):
        # Warm-up or indicators not ready? stop
        if self.IsWarmingUp or not self.fast.IsReady or not self.slow.IsReady:
            return

        # Make sure we have bars for BOTH QQQ and SQQQ this hour
        qqq_bar  = data.Bars[self.qqq]  if data.Bars.ContainsKey(self.qqq)  else None
        sqqq_bar = data.Bars[self.sqqq] if data.Bars.ContainsKey(self.sqqq) else None
        if qqq_bar is None or sqqq_bar is None:
            return  # no trading if either bar is missing

        price = sqqq_bar.Close

        fast_val = self.fast.Current.Value
        slow_val = self.slow.Current.Value
        macd_line = fast_val - slow_val

        # Crossover detection (use previous EMA values to detect a cross on this bar)
        cross_up = (
            self.prev_fast is not None and self.prev_slow is not None
            and self.prev_fast <= self.prev_slow and fast_val > slow_val
        )
        cross_down = (
            self.prev_fast is not None and self.prev_slow is not None
            and self.prev_fast >= self.prev_slow and fast_val < slow_val
        )

        if not self.in_position:
            # SHORT SQQQ when QQQ turns bullish (fast crosses above slow; MACD positive)
            if cross_up and macd_line > 0:
                qty = self.CalculateOrderQuantity(self.sqqq, -1.0)  # target -100% allocation
                if qty < 0:
                    self.MarketOrder(self.sqqq, qty)
                    self.in_position = True
                    self.entry_price = price
                    self.trail_min_price = price   # for shorts, track the LOWEST price after entry
                    self.trade_count += 1
                    self.Debug(f"SHORT {abs(qty)} SQQQ @ {price:.2f} on {self.Time}")
        else:
            # Update trailing minimum (best move for a short is down)
            if price < self.trail_min_price:
                self.trail_min_price = price

            # Draw-up from the post-entry low (adverse move for a short)
            denom = max(self.trail_min_price, 1e-9)
            drawup = (price - self.trail_min_price) / denom

            # Exit if trailing stop hit OR QQQ momentum flips bearish while MACD still > 0
            if drawup >= self.trailing_stop_pct or (cross_down and macd_line > 0):
                qty = self.Portfolio[self.sqqq].Quantity
                if qty < 0:
                    self.MarketOrder(self.sqqq, -qty)  # cover
                    self.Debug(f"COVER {abs(qty)} SQQQ @ {price:.2f} on {self.Time} (Drawup: {drawup:.2%})")
                self.in_position = False
                self.entry_price = None
                self.trail_min_price = None

        # Store EMAs for next-bar crossover detection
        self.prev_fast = fast_val
        self.prev_slow = slow_val

    def OnEndOfAlgorithm(self):
        # Ensure flat at the end
        if self.Portfolio[self.sqqq].Invested:
            self.Liquidate(self.sqqq)

        self.Log(f"Total SQQQ SHORT Trades: {self.trade_count}")
        self.Log(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue:.2f}")

        total_return = (self.Portfolio.TotalPortfolioValue / 100000 - 1) * 100
        years = (self.EndDate - self.StartDate).days / 365.25
        annualized_return = ((self.Portfolio.TotalPortfolioValue / 100000) ** (1 / years) - 1) * 100

        self.Log(f"Total Return: {total_return:.2f}%")
        self.Log(f"Annualized Return: {annualized_return:.2f}%")
