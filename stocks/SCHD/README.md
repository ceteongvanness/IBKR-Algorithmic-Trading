# High Win Rate SCHD Stock Trading Algorithm

## 📈 Overview

This QuantConnect algorithm implements a high win rate trading strategy specifically designed for SCHD (Schwab US Dividend Equity ETF) and optimized for smaller trading accounts ($5,000-$10,000). SCHD tracks high-quality dividend-paying US stocks and is ideal for conservative growth strategies focused on income and capital preservation.

## 🎯 Strategy Objectives

- **Primary Goal**: Achieve 70-80% win rate through dividend-focused approach
- **Secondary Goal**: Optimize for small account dividend growth strategy
- **Income Focus**: Leverage SCHD's quarterly dividend schedule
- **Risk Management**: Conservative approach suitable for income-focused investors

## 💰 Why SCHD for Small Accounts?

### SCHD Advantages
- **Quality Dividend Focus**: Holdings are screened for dividend quality and sustainability
- **Low Expense Ratio**: 0.06% annual fee (very reasonable for active management)
- **Moderate Price**: ~$80 per share (accessible for small accounts)
- **Quarterly Dividends**: Predictable income stream (~2.5-3.5% yield)
- **Quality Holdings**: Large-cap dividend aristocrats and kings

### Small Account Benefits
- **Stable Growth**: Less volatile than growth ETFs
- **Predictable Patterns**: Dividend schedule creates trading opportunities
- **Income Generation**: Quarterly dividends supplement trading profits
- **Lower Stress**: Conservative nature reduces emotional trading pressure

## 🔧 Algorithm Features

### Dividend-Aware Strategy

#### Quarterly Dividend Schedule Integration
- **Dividend Months**: March, June, September, December
- **Boost Periods**: 2 weeks before typical ex-dividend dates
- **Position Management**: Increased long bias during dividend approach
- **Risk Protection**: Avoid shorts during dividend periods

#### Entry Requirements (10+ Conditions for Long)
1. **Long-term Uptrend**: Price > 200-day SMA (dividend sustainability)
2. **Medium-term Trend**: EMA fast > EMA slow
3. **Current Trend**: Price > 50-day EMA
4. **Market Regime**: Bullish or neutral environment
5. **Sector Strength**: Dividend sector momentum positive
6. **Conservative Momentum**: RSI 35-70 range
7. **MACD Confirmation**: Bullish trend signal
8. **Mean Reversion**: Price near Bollinger Band middle (buy dips)
9. **Volume Adequate**: Sufficient ETF liquidity
10. **Time Filter**: Avoid first/last hour of trading
11. **Trade Size**: Minimum $400 position value
12. **Dividend Boost**: Extra condition during dividend approach periods

### Small Account Optimizations ($6,319)

#### Position Sizing
- **Maximum Position**: 85% of account (conservative for dividend ETF)
- **Minimum Trade**: $400 per position
- **Daily Limit**: 2 trades maximum
- **Emergency Stop**: 6% maximum single trade loss

#### Risk Management
- **Stop Loss**: 3% (wider for stable dividend ETF)
- **Take Profit**: 5% (higher target for lower volatility)
- **Hold Time**: 60 minutes minimum to 14 days maximum
- **Dividend Protection**: Close shorts before ex-dividend periods

## 🚀 Getting Started

### Prerequisites
- QuantConnect account (free registration)
- $3,000+ trading capital (optimal: $5,000+)
- Understanding of dividend investing
- Basic knowledge of ETF characteristics

### Setup Instructions

1. **Algorithm Configuration**
   ```python
   # Optimized for your account size
   self.SetCash(6319)               # Your current capital
   self.min_trade_value = 400       # Minimum trade size
   self.max_trades_per_day = 2      # Conservative daily limit
   self.stop_loss_pct = 0.03        # 3% stop loss
   self.take_profit_pct = 0.05      # 5% take profit
   ```

2. **Deploy to QuantConnect**
   - Copy algorithm to QuantConnect Algorithm Lab
   - Set start/end dates for backtesting
   - Run backtest to validate performance

3. **Monitor Performance**
   - Track win rate (target: 70%+)
   - Monitor dividend capture opportunities
   - Adjust parameters based on market conditions

## 📊 Expected Performance

### Performance Metrics (Small Account)
- **Target Win Rate**: 70-80%
- **Average Win**: 3-5%
- **Average Loss**: 2-3%
- **Monthly Return**: 4-8% (including dividends)
- **Maximum Drawdown**: 8-12%
- **Trades per Month**: 6-12
- **Hold Time**: 2-7 days average

### Dividend Enhancement
- **Quarterly Boosts**: Enhanced activity during dividend months
- **Income Supplement**: ~3% annual dividend yield adds to returns
- **Stability Factor**: Dividend focus reduces overall portfolio volatility

## 💡 Trading Strategy Logic

### Long Entry Strategy (Dividend-Focused)
```
Long Entry Checklist (10+ required):
✓ Price > 200-day SMA (long-term dividend sustainability)
✓ EMA Fast > EMA Slow (medium-term uptrend)
✓ Price > 50-day EMA (current uptrend)
✓ Market Regime = Bullish/Neutral
✓ Dividend Sector Strength ≠ Weak
✓ RSI 35-70 (conservative momentum)
✓ MACD > Signal (trend confirmation)
✓ Price ≤ BB Middle * 1.02 (buy dip setup)
✓ Volume adequate for ETF trading
✓ Time filter (avoid market open/close)
✓ Trade size ≥ $400 (minimum position)
✓ Dividend boost period (bonus condition)
```

### Dividend Calendar Strategy
```python
def dividend_calendar_strategy():
    """Coordinate trades with SCHD dividend schedule"""
    
    # Q1: March dividend approach
    if month == 3 and day >= 10:
        increase_long_bias()
        
    # Q2: June dividend approach  
    if month == 6 and day >= 10:
        increase_long_bias()
        
    # Q3: September dividend approach
    if month == 9 and day >= 10:
        increase_long_bias()
        
    # Q4: December dividend approach
    if month == 12 and day >= 10:
        increase_long_bias()
```

### Risk Management Framework
```python
def risk_management_rules():
    """SCHD-specific risk management"""
    
    rules = {
        # Position limits
        'max_position_pct': 0.85,        # 85% maximum position
        'min_trade_value': 400,          # $400 minimum trade
        'max_daily_trades': 2,           # Conservative limit
        
        # Risk controls
        'stop_loss': 0.03,               # 3% stop loss
        'take_profit': 0.05,             # 5% take profit
        'emergency_stop': 0.06,          # 6% emergency exit
        
        # Time management
        'min_hold_minutes': 60,          # 1 hour minimum
        'max_hold_days': 14,             # 2 week maximum
        
        # Dividend protection
        'avoid_shorts_in_dividend_period': True,
        'boost_longs_near_ex_dividend': True
    }
    return rules
```

## 📈 Dividend-Optimized Features

### Quarterly Dividend Boost Strategy
```python
def dividend_boost_analysis():
    """Enhanced trading during dividend periods"""
    
    # Typical SCHD dividend schedule
    dividend_months = [3, 6, 9, 12]  # Quarterly
    
    for month in dividend_months:
        if current_month == month and 10 <= current_day <= 25:
            # Dividend boost period active
            benefits = [
                'increased_long_bias',       # Favor long positions
                'reduced_short_activity',    # Avoid dividend risk
                'extended_hold_periods',     # Hold through ex-dividend
                'quality_over_quantity'      # Fewer but better trades
            ]
            return benefits
```

### Dividend Capture Enhancement
```python
def dividend_capture_opportunities():
    """Optional dividend capture integration"""
    
    # Strategy can be enhanced to:
    # 1. Buy SCHD 2-3 days before ex-dividend
    # 2. Hold through ex-dividend date
    # 3. Sell after dividend payment
    # 4. Capture ~0.6-0.9% quarterly dividend
    
    capture_benefits = {
        'quarterly_income': '0.6-0.9% per quarter',
        'annual_yield': '2.5-3.5% from dividends',
        'stability': 'Reduced volatility during hold',
        'compound_growth': 'Reinvested dividends boost returns'
    }
    return capture_benefits
```

## 🛡️ Risk Management for Dividend ETF

### Conservative Approach Benefits
```python
def conservative_risk_benefits():
    """Why conservative approach works for SCHD"""
    
    benefits = {
        # Lower volatility than growth ETFs
        'volatility_reduction': 'SCHD typically 15-20% volatility vs 25%+ for QQQ',
        
        # Predictable dividend income
        'income_stability': 'Quarterly dividends provide predictable returns',
        
        # Quality holdings
        'fundamental_strength': 'Holdings screened for dividend sustainability',
        
        # Small account friendly
        'position_sizing': 'Larger positions possible with lower volatility',
        
        # Emotional benefits
        'stress_reduction': 'Less volatile = easier to hold positions'
    }
    return benefits
```

### Emergency Procedures for Small Accounts
```python
def emergency_procedures():
    """Small account protection for SCHD trading"""
    
    # Account value protection
    if account_drawdown > 0.15:  # 15% drawdown
        reduce_position_sizes()
        increase_stop_losses()
        require_higher_conviction()
    
    # Single trade protection
    if single_trade_loss > 0.06:  # 6% single trade loss
        immediate_exit()
        review_risk_parameters()
    
    # Dividend period protection
    if approaching_ex_dividend():
        close_all_short_positions()
        consider_dividend_capture()
```

## 📊 Performance Monitoring

### Key Metrics Dashboard
```python
def performance_metrics():
    """Track SCHD-specific performance"""
    
    metrics = {
        # Trading performance
        'win_rate': 'Target: 70%+',
        'average_win': 'Target: 3-5%',
        'average_loss': 'Target: 2-3%',
        'monthly_return': 'Target: 4-8%',
        
        # Dividend performance
        'dividend_periods_captured': 'Quarterly tracking',
        'dividend_boost_success': 'Enhanced period performance',
        'ex_dividend_timing': 'Accuracy of dividend calendar',
        
        # Risk metrics
        'maximum_drawdown': 'Target: <12