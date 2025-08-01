# High Win Rate SPLG Stock Trading Algorithm

## 📈 Overview

This QuantConnect algorithm implements a high win rate trading strategy specifically designed for SPLG (SPDR Portfolio S&P 500 ETF) and optimized for smaller trading accounts ($5,000-$10,000). SPLG provides the same S&P 500 exposure as SPY but with a lower expense ratio (0.02% vs 0.09%) and lower share price, making it ideal for smaller accounts.

## 🎯 Strategy Objectives

- **Primary Goal**: Maximize win rate (65-75%) with capital preservation focus
- **Secondary Goal**: Optimize for small account constraints and position sizing
- **Risk Management**: Tight risk control suitable for limited capital
- **Target Trades**: 2-4 per week with high conviction entries

## 💰 Small Account Optimization

### Why SPLG Over SPY for Small Accounts?
- **Lower Share Price**: ~$55 vs ~$550 for SPY (easier position sizing)
- **Lower Expense Ratio**: 0.02% vs 0.09% (cost savings over time)
- **Same Exposure**: Tracks S&P 500 identically to SPY
- **Better Liquidity**: Suitable for accounts under $10,000
- **Fractional Benefits**: Easier to achieve target allocation percentages

### Capital Requirements
- **Minimum Account**: $3,000 recommended
- **Optimal Account**: $5,000-$15,000
- **Current Optimization**: $6,319 (your account size)
- **Position Sizing**: $300-$500 minimum trade size

## 🔧 Algorithm Features

### Small Account Adaptations

#### Position Sizing
- **Maximum Position**: 90% of account (vs 95% for larger accounts)
- **Minimum Trade Size**: $500 per position
- **Risk per Trade**: 2% of account maximum
- **Daily Trade Limit**: 2 trades maximum to preserve capital

#### Risk Management (Optimized for $6,319)
- **Stop Loss**: 2% (tighter than standard 2.5%)
- **Take Profit**: 3.5% (achievable target for small accounts)
- **Emergency Stop**: 5% maximum loss protection
- **Position Concentration**: Limited to prevent over-exposure

#### Entry Requirements (9+ Conditions for Long)
1. **Trend Alignment**: Multiple EMA alignment
2. **Higher Timeframe**: Daily EMA confirmation
3. **Market Regime**: Bullish or neutral environment
4. **Momentum**: RSI 45-70 range
5. **MACD**: Bullish crossover confirmation
6. **Mean Reversion**: Price near Bollinger Band middle
7. **Volume**: Above-average participation
8. **Time Filter**: Avoid first/last 30 minutes
9. **Trade Size**: Minimum $500 position value
10. **Risk Check**: Position fits risk parameters

## 🚀 Getting Started

### Prerequisites
- QuantConnect account (free)
- $3,000+ trading capital (optimal: $5,000+)
- Understanding of ETF trading
- Basic technical analysis knowledge

### Setup Instructions

1. **Account Setup**
   ```python
   # In QuantConnect Algorithm Lab
   self.SetCash(6319)  # Your current capital
   self.min_trade_value = 500  # Minimum trade size
   self.max_trades_per_day = 2  # Daily limit
   ```

2. **Risk Configuration**
   ```python
   # Conservative settings for small account
   self.stop_loss_pct = 0.02     # 2% stop loss
   self.take_profit_pct = 0.035  # 3.5% take profit
   self.max_position_size = 0.90 # 90% max position
   ```

3. **Deploy and Monitor**
   - Start with paper trading
   - Monitor daily for 2 weeks
   - Adjust parameters based on performance

## 📊 Expected Performance (Small Account)

### Performance Metrics
- **Target Win Rate**: 65-75%
- **Average Win**: 2.5-3.5%
- **Average Loss**: 1.5-2.0%
- **Monthly Return**: 3-8% (higher volatility for small accounts)
- **Maximum Drawdown**: 10-15%
- **Trades per Month**: 8-15

### Small Account Benefits
- **Higher Position Concentration**: Can achieve better returns per trade
- **Faster Compounding**: Smaller base grows faster percentage-wise
- **Lower Fees**: SPLG's low expense ratio helps small accounts
- **Flexibility**: Easier to adjust position sizes

## 💡 Trading Strategy Logic

### Entry Strategy (High Conviction Required)
```
Long Entry Checklist (9+ required):
✓ EMA Fast > EMA Slow (short-term uptrend)
✓ Price > EMA Trend (medium-term uptrend)  
✓ Price > Daily EMA (long-term uptrend)
✓ Market Regime = Bullish/Neutral
✓ RSI 45-70 (momentum not extreme)
✓ MACD > Signal (trend confirmation)
✓ Price ≤ BB Middle * 1.01 (buy dip setup)
✓ Volume > Average * 0.8 (participation)
✓ Trade Size ≥ $500 (minimum position)
```

### Position Sizing Calculation
```python
def calculate_position_size(account_value, stock_price):
    # Conservative approach for small accounts
    max_position_value = account_value * 0.90  # 90% max
    shares = int(max_position_value / stock_price)
    
    # Ensure minimum trade size
    if shares * stock_price < 500:
        return 0  # Skip trade if too small
    
    return shares
```

### Risk Management Rules
```python
def risk_management_rules():
    rules = {
        'max_daily_trades': 2,           # Preserve capital
        'emergency_stop': 0.05,          # 5% maximum loss
        'profit_target': 0.035,          # 3.5% take profit
        'stop_loss': 0.02,               # 2% stop loss
        'min_hold_time': 45,             # 45 minutes minimum
        'end_of_day_exit': True          # No overnight risk
    }
    return rules
```

## 📈 Small Account Growth Strategy

### Phase 1: Capital Preservation ($6,319 - $10,000)
- **Focus**: High win rate, tight risk control
- **Target**: 4-6% monthly returns
- **Trades**: 2-3 per week maximum
- **Risk**: 2% per trade maximum

### Phase 2: Steady Growth ($10,000 - $25,000)  
- **Focus**: Consistent compounding
- **Target**: 3-5% monthly returns
- **Trades**: 3-4 per week
- **Risk**: 2-2.5% per trade

### Phase 3: Scaling Up ($25,000+)
- **Focus**: Multiple strategies
- **Target**: 2-4% monthly returns
- **Trades**: Consider multiple assets
- **Risk**: 1.5-2% per trade

## 🛡️ Risk Management for Small Accounts

### Capital Preservation Rules

#### Daily Limits
```python
# Maximum trades per day
if self.daily_trade_count >= 2:
    return  # No more trades today

# Maximum daily loss protection
if daily_pnl < -account_value * 0.03:  # 3% daily loss limit
    stop_all_trading()
```

#### Position Size Validation
```python
def validate_trade_size(shares, price, account_value):
    trade_value = shares * price
    
    # Minimum trade size
    if trade_value < 500:
        return False, "Trade too small"
    
    # Maximum position size  
    if trade_value > account_value * 0.90:
        return False, "Position too large"
    
    return True, "Valid trade size"
```

### Emergency Procedures
```python
def emergency_stops():
    """Emergency protection for small accounts"""
    
    # Account drawdown protection
    if current_equity < initial_equity * 0.85:  # 15% drawdown
        reduce_position_sizes()
        increase_stop_losses()
    
    # Single trade protection
    if position_loss > account_value * 0.05:  # 5% single trade loss
        immediate_exit()
```

## 📊 Performance Monitoring

### Daily Metrics to Track
- **Account Value**: Current equity
- **Daily P&L**: Today's profit/loss
- **Win Rate**: Percentage of winning trades
- **Average Trade**: Profit per trade
- **Risk Utilization**: Percentage of capital at risk

### Weekly Review Checklist
- [ ] Overall win rate above 60%
- [ ] No single loss greater than 3%
- [ ] Daily trade limits respected
- [ ] Position sizing appropriate
- [ ] Emergency stops functioning

### Monthly Analysis
- [ ] Monthly return target achieved
- [ ] Drawdown within acceptable limits
- [ ] Risk-reward ratio maintained
- [ ] Account growth trajectory on track

## 🔧 Customization for Your Account

### Conservative Settings (Higher Win Rate)
```python
# Ultra-conservative for capital preservation
self.stop_loss_pct = 0.015       # 1.5% stop loss
self.take_profit_pct = 0.025     # 2.5% take profit  
self.max_position_size = 0.75    # 75% max position
self.max_trades_per_day = 1      # One trade per day
min_conditions_required = 10     # Highest selectivity
```

### Moderate Settings (Current Default)
```python
# Balanced approach for steady growth
self.stop_loss_pct = 0.02        # 2% stop loss
self.take_profit_pct = 0.035     # 3.5% take profit
self.max_position_size = 0.90    # 90% max position
self.max_trades_per_day = 2      # Two trades per day
min_conditions_required = 9      # High selectivity
```

### Growth Settings (Higher Returns)
```python
# More aggressive once account grows
self.stop_loss_pct = 0.025       # 2.5% stop loss
self.take_profit_pct = 0.04      # 4% take profit
self.max_position_size = 0.95    # 95% max position
self.max_trades_per_day = 3      # Three trades per day
min_conditions_required = 8      # Moderate selectivity
```

## 📚 Educational Resources

### Small Account Trading
- **"Trading with Small Accounts"**: Position sizing strategies
- **"Risk Management Basics"**: Capital preservation techniques
- **"ETF Trading Guide"**: Understanding SPLG vs SPY differences

### Technical Analysis for ETFs
- **"ETF Momentum Strategies"**: Trend following in index funds
- **"Mean Reversion in ETFs"**: Counter-trend opportunities
- **"Volume Analysis"**: Understanding ETF liquidity patterns

## ⚠️ Small Account Specific Risks

### Unique Challenges
- **Limited Diversification**: Single position concentration
- **Overtrading Temptation**: Too many trades erode capital
- **Emotional Pressure**: Every loss feels significant
- **Growth Pressure**: Unrealistic return expectations

### Risk Mitigation
- **Strict Position Sizing**: Never exceed risk limits
- **Trade Frequency Limits**: Quality over quantity
- **Emotional Discipline**: Stick to mechanical rules
- **Realistic Expectations**: Focus on percentage returns

## 📞 Support and Resources

### Algorithm-Specific Support
- **Code Documentation**: Detailed comments in algorithm
- **Parameter Adjustment**: Guidance for different account sizes
- **Performance Tracking**: Built-in logging and analysis

### QuantConnect Resources  
- **Paper Trading**: Test with virtual money first
- **Backtesting**: Historical performance validation
- **Community Forum**: Small account trading discussions

## 📝 Version History

- **v1.0**: Initial SPLG algorithm for small accounts
- **Current**: Optimized for $6,319 account size with tight risk controls

## 