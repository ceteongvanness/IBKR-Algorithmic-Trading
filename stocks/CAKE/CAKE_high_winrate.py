from AlgorithmImports import *
import numpy as np

class OptimizedCAKEAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        # Set backtest period 
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        
        # Set initial cash
        self.SetCash(6319)
        
        # Add CAKE (The Cheesecake Factory Inc.) - Restaurant/hospitality stock
        self.cake = self.AddEquity("CAKE", Resolution.Minute).Symbol
        self.SetBenchmark(self.cake)
        
        # Initialize indicators
        self.Setup_Indicators()
        
        # OPTIMIZED Risk management for restaurant/hospitality stock
        self.max_position_size = 0.70      # 70% for cyclical restaurant stock
        self.base_stop_loss = 0.06         # 6% stop (moderate for restaurant volatility)
        self.base_take_profit = 0.10       # 10% target (reasonable for cyclical stock)
        self.quick_profit_threshold = 0.04 # 4% quick profit
        self.min_trade_value = 250         # Minimum trade size
        self.max_trades_per_day = 2        # Moderate frequency
        
        # Restaurant/hospitality specific parameters
        self.consumer_discretionary_threshold = 50  # Consumer spending sentiment
        self.seasonal_boost_months = [11, 12, 5, 6] # Holiday and summer seasons
        self.earnings_volatility_factor = 1.5      # Restaurants have volatile earnings
        
        # Economic sensitivity factors
        self.economic_sentiment = "NEUTRAL"
        self.seasonal_period = "NORMAL"
        self.earnings_proximity = "CLEAR"
        self.covid_recovery_phase = "NORMAL"  # Post-COVID recovery tracking
        
        # Trade tracking for optimization
        self.entry_price = 0
        self.position_entry_time = None
        self.daily_trade_count = 0
        self.total_trades = 0
        self.win_count = 0
        self.loss_count = 0
        self.monthly_returns = []
        
        # Optimization parameters for restaurant stock
        self.optimization_params = {
            'stop_loss_variants': [0.045, 0.06, 0.075, 0.09],
            'take_profit_variants': [0.08, 0.10, 0.12, 0.15],
            'position_size_variants': [0.60, 0.70, 0.80],
            'rsi_ranges': [(25, 75), (30, 70), (35, 65)],
            'seasonal_boost': [True, False]
        }
        
        # Current optimization set
        self.current_stop = 0.06
        self.current_profit = 0.10
        self.current_position = 0.70
        self.current_rsi = (30, 70)
        self.use_seasonal_boost = True
        
        # Schedule functions
        self.Schedule.On(
            self.DateRules.EveryDay(self.cake), 
            self.TimeRules.AfterMarketOpen(self.cake, 5), 
            self.ResetDailyCounters
        )
        
        self.Schedule.On(
            self.DateRules.Every(DayOfWeek.Monday), 
            self.TimeRules.AfterMarketOpen(self.cake, 60), 
            self.WeeklyRestaurantAnalysis
        )
        
        self.Schedule.On(
            self.DateRules.MonthStart(self.cake), 
            self.TimeRules.AfterMarketOpen(self.cake, 30), 
            self.MonthlySeasonalAnalysis
        )
        
        # Warm up
        self.SetWarmUp(60)
        
    def Setup_Indicators(self):
        # Restaurant stock optimized indicators (medium responsiveness)
        self.ema_fast = self.EMA(self.cake, 12, Resolution.Daily)     # Moderate for restaurant
        self.ema_slow = self.EMA(self.cake, 26, Resolution.Daily)     # Standard
        self.ema_trend = self.EMA(self.cake, 50, Resolution.Daily)    # Long term trend
        
        # Higher timeframe for stability
        self.sma_200 = self.SMA(self.cake, 200, Resolution.Daily)     # Long-term health
        
        # RSI for cyclical momentum
        self.rsi = self.RSI(self.cake, 14, Resolution.Daily)          # Standard RSI
        
        # MACD for trend confirmation
        self.macd = self.MACD(self.cake, 12, 26, 9, Resolution.Daily)
        
        # Bollinger Bands for volatility
        self.bb = self.BB(self.cake, 20, 2, Resolution.Daily)
        
        # Volume indicators (important for restaurant stocks)
        self.volume_sma = self.SMA(self.cake, 20, Resolution.Daily, Field.Volume)
        self.volume_surge = self.SMA(self.cake, 5, Resolution.Daily, Field.Volume)
        
        # ATR for volatility
        self.atr = self.ATR(self.cake, 14, Resolution.Daily)
        
        # Consumer discretionary sector strength (using CAKE as proxy)
        self.sector_rsi = self.RSI(self.cake, 21, Resolution.Weekly)
        
        # Economic recovery tracking (post-COVID)
        self.recovery_ema = self.EMA(self.cake, 60, Resolution.Daily)  # Recovery trend
        
    def ResetDailyCounters(self):
        """Reset daily counters and update analysis"""
        self.daily_trade_count = 0
        self.UpdateEconomicSentiment()
        
    def WeeklyRestaurantAnalysis(self):
        """Weekly restaurant industry analysis"""
        self.CheckEarningsProximity()
        self.AnalyzeSectorMomentum()
        self.AssessCovidRecoveryPhase()
        
    def MonthlySeasonalAnalysis(self):
        """Monthly seasonal analysis for restaurant business"""
        current_month = self.Time.month
        
        if current_month in self.seasonal_boost_months:
            self.seasonal_period = "PEAK"    # Holiday/summer seasons
        elif current_month in [1, 2, 3, 9]:  # Slow months
            self.seasonal_period = "SLOW"
        else:
            self.seasonal_period = "NORMAL"
            
        self.Log(f"Seasonal Period: {self.seasonal_period} (Month: {current_month})")
        
    def UpdateEconomicSentiment(self):
        """Update economic sentiment based on price vs recovery trend"""
        if not self.recovery_ema.IsReady:
            return
            
        current_price = self.Securities[self.cake].Price
        recovery_trend = self.recovery_ema.Current.Value
        
        # Economic sentiment based on recovery
        if current_price > recovery_trend * 1.1:
            self.economic_sentiment = "STRONG_RECOVERY"
        elif current_price > recovery_trend * 1.03:
            self.economic_sentiment = "MODERATE_RECOVERY"
        elif current_price < recovery_trend * 0.90:
            self.economic_sentiment = "ECONOMIC_STRESS"
        else:
            self.economic_sentiment = "NEUTRAL"
            
    def CheckEarningsProximity(self):
        """Check for CAKE earnings (quarterly)"""
        current_month = self.Time.month
        
        # CAKE typical earnings months
        earnings_months = [2, 4, 7, 10]  # Feb, Apr, Jul, Oct
        
        if current_month in earnings_months:
            day = self.Time.day
            if 15 <= day <= 28:
                self.earnings_proximity = "NEAR"
            else:
                self.earnings_proximity = "CLEAR"
        else:
            self.earnings_proximity = "CLEAR"
            
    def AnalyzeSectorMomentum(self):
        """Analyze consumer discretionary sector momentum"""
        if not self.sector_rsi.IsReady:
            return
            
        sector_rsi = self.sector_rsi.Current.Value
        
        if sector_rsi > 60:
            self.consumer_discretionary_momentum = "STRONG"
        elif sector_rsi < 40:
            self.consumer_discretionary_momentum = "WEAK"
        else:
            self.consumer_discretionary_momentum = "NEUTRAL"
            
    def AssessCovidRecoveryPhase(self):
        """Assess post-COVID recovery phase for restaurant industry"""
        current_price = self.Securities[self.cake].Price
        
        # Simple recovery assessment based on price levels
        if current_price > 45:  # Pre-COVID levels for CAKE
            self.covid_recovery_phase = "FULL_RECOVERY"
        elif current_price > 35:
            self.covid_recovery_phase = "STRONG_RECOVERY"
        elif current_price > 25:
            self.covid_recovery_phase = "MODERATE_RECOVERY"
        else:
            self.covid_recovery_phase = "EARLY_RECOVERY"
    
    def OnData(self, data):
        if self.IsWarmingUp:
            return
            
        if not self.AllIndicatorsReady():
            return
            
        if not