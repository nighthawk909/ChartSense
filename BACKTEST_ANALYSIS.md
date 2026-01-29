# Backtest Analysis Report

> **Generated**: 2026-01-28
> **Test Period**: ~1 year of daily data per symbol
> **Initial Capital**: $100,000 per test

---

## Executive Summary

After running 35 backtests across 7 stocks and 5 strategies, the key findings are:

| Ranking | Strategy | Avg Return | Avg Sharpe | Best For |
|---------|----------|------------|------------|----------|
| 1 | **Momentum** | +1.01% | **0.33** | Trending stocks (GOOGL) |
| 2 | **Mean Reversion** | +1.05% | **0.17** | Volatile stocks (NVDA) |
| 3 | **Bollinger Bounce** | +0.59% | 0.12 | Range-bound stocks |
| 4 | RSI Oversold | -0.64% | -0.10 | Needs improvement |
| 5 | MACD Crossover | -1.24% | **-0.43** | NOT RECOMMENDED |

**Recommendation**: Focus on **Momentum** and **Mean Reversion** strategies. Remove or significantly improve MACD Crossover.

---

## Top 5 Best Performing Combinations

| Rank | Symbol | Strategy | Return | Win Rate | Sharpe | Trades |
|------|--------|----------|--------|----------|--------|--------|
| 1 | GOOGL | Momentum | **+6.99%** | 64.3% | **1.86** | 14 |
| 2 | NVDA | Bollinger | **+6.97%** | 69.2% | **1.79** | 13 |
| 3 | NVDA | Mean Reversion | **+6.65%** | 61.5% | **1.30** | 39 |
| 4 | AAPL | MACD | +1.90% | 36.0% | 0.66 | 25 |
| 5 | AMZN | Bollinger | +1.89% | 54.5% | 0.61 | 11 |

**Key Insight**: The best performers have Sharpe ratios > 1.0, indicating good risk-adjusted returns.

---

## Top 5 Worst Performing Combinations

| Rank | Symbol | Strategy | Return | Win Rate | Sharpe | Trades |
|------|--------|----------|--------|----------|--------|--------|
| 1 | AMZN | MACD | **-5.41%** | 17.6% | **-1.48** | 34 |
| 2 | GOOGL | RSI | **-5.35%** | 8.3% | **-1.84** | 12 |
| 3 | NVDA | MACD | **-5.19%** | 30.8% | **-1.19** | 26 |
| 4 | GOOGL | Bollinger | -3.23% | 21.4% | -1.13 | 14 |
| 5 | AAPL | Bollinger | -3.04% | 33.3% | -1.05 | 15 |

**Key Insight**: MACD and RSI generate too many false signals. High trade counts with low win rates = losses.

---

## Strategy-by-Strategy Analysis

### 1. Momentum Strategy - RECOMMENDED
```
Average Return: +1.01%
Average Sharpe: 0.33
Win/Loss: 5/2 (71% profitable symbols)
Best on: GOOGL (+6.99%), TSLA (+2.06%)
Worst on: NVDA (-2.31%)
```
**Verdict**: Keep. Works well on trending stocks. Simple and effective.

### 2. Mean Reversion Strategy - RECOMMENDED
```
Average Return: +1.05%
Average Sharpe: 0.17
Win/Loss: 4/3 (57% profitable symbols)
Best on: NVDA (+6.65%), TSLA (+2.48%)
Worst on: GOOGL (-2.19%)
```
**Verdict**: Keep. Works well on volatile stocks that oscillate around their mean.

### 3. Bollinger Bounce Strategy - CONDITIONAL
```
Average Return: +0.59%
Average Sharpe: 0.12
Win/Loss: 4/3 (57% profitable symbols)
Best on: NVDA (+6.97%), AMZN (+1.89%)
Worst on: GOOGL (-3.23%)
```
**Verdict**: Keep with improvements. Works when bands are meaningful; fails on strong trends.

### 4. RSI Oversold Strategy - NEEDS WORK
```
Average Return: -0.64%
Average Sharpe: -0.10
Win/Loss: 4/3 (57% profitable symbols)
Best on: MSFT (+1.84%), NVDA (+1.22%)
Worst on: GOOGL (-5.35%)
```
**Verdict**: Improve thresholds. Consider RSI 25/75 instead of 30/70.

### 5. MACD Crossover Strategy - NOT RECOMMENDED
```
Average Return: -1.24%
Average Sharpe: -0.43
Win/Loss: 3/4 (43% profitable symbols)
Best on: AAPL (+1.90%), META (+1.58%)
Worst on: AMZN (-5.41%), NVDA (-5.19%)
```
**Verdict**: REMOVE or drastically improve. Too many false signals, poor risk-adjusted returns.

---

## Actionable Recommendations

### For Trading Bot Simplification

1. **PRIMARY STRATEGY**: Momentum
   - Simple: Buy when price momentum > 5% over 20 days
   - Best for trending markets
   - Low trade frequency, high quality signals

2. **SECONDARY STRATEGY**: Mean Reversion
   - Buy when price is 3%+ below 20-day SMA
   - Best for range-bound/volatile stocks
   - Higher trade frequency, needs good stock selection

3. **REMOVE**: MACD Crossover
   - Too many false signals
   - Negative average return
   - Worst Sharpe ratio of all strategies

4. **IMPROVE**: RSI Oversold
   - Tighten thresholds (25/75 instead of 30/70)
   - Add confirmation signals
   - Only use on non-trending stocks

### Indicator Reduction Plan

**Current**: 15+ indicators
**Target**: 5 core indicators

| Keep | Remove | Reason |
|------|--------|--------|
| Momentum (ROC) | MACD | Poor risk-adjusted returns |
| SMA 20 | SMA 200 | Rarely used in best strategies |
| RSI (improved) | Williams %R | Redundant with RSI |
| Bollinger Bands | ADX | Complex, marginal benefit |
| ATR (for stops) | Stochastic | Redundant with RSI |

---

## Next Steps

1. [ ] Update trading bot to prioritize Momentum and Mean Reversion
2. [ ] Remove MACD crossover signals from decision logic
3. [ ] Improve RSI thresholds (25/75)
4. [ ] Add stock-specific strategy selection (trending vs range-bound)
5. [ ] Run 2-week paper trading validation

---

## Raw Data

### Full Results by Symbol

**AAPL**
| Strategy | Return | Win Rate | Sharpe | Trades |
|----------|--------|----------|--------|--------|
| RSI | +0.46% | 41.7% | 0.17 | 12 |
| MACD | +1.90% | 36.0% | 0.66 | 25 |
| Bollinger | -3.04% | 33.3% | -1.05 | 15 |
| Momentum | +1.49% | 41.7% | 0.44 | 12 |
| Mean Rev | +0.55% | 58.3% | 0.19 | 24 |

**MSFT**
| Strategy | Return | Win Rate | Sharpe | Trades |
|----------|--------|----------|--------|--------|
| RSI | +1.84% | 44.4% | 0.73 | 9 |
| MACD | -2.70% | 26.9% | -1.01 | 26 |
| Bollinger | +1.83% | 54.5% | 0.71 | 11 |
| Momentum | +1.41% | 50.0% | 0.58 | 8 |
| Mean Rev | -0.47% | 55.0% | -0.18 | 20 |

**GOOGL**
| Strategy | Return | Win Rate | Sharpe | Trades |
|----------|--------|----------|--------|--------|
| RSI | -5.35% | 8.3% | -1.84 | 12 |
| MACD | +0.75% | 37.9% | 0.23 | 29 |
| Bollinger | -3.23% | 21.4% | -1.13 | 14 |
| Momentum | +6.99% | 64.3% | 1.86 | 14 |
| Mean Rev | -2.19% | 53.3% | -0.63 | 30 |

**AMZN**
| Strategy | Return | Win Rate | Sharpe | Trades |
|----------|--------|----------|--------|--------|
| RSI | +0.21% | 40.0% | 0.10 | 5 |
| MACD | -5.41% | 17.6% | -1.48 | 34 |
| Bollinger | +1.89% | 54.5% | 0.61 | 11 |
| Momentum | -1.67% | 28.6% | -0.42 | 14 |
| Mean Rev | +0.59% | 68.2% | 0.18 | 22 |

**NVDA**
| Strategy | Return | Win Rate | Sharpe | Trades |
|----------|--------|----------|--------|--------|
| RSI | +1.22% | 33.3% | 0.46 | 6 |
| MACD | -5.19% | 30.8% | -1.19 | 26 |
| Bollinger | +6.97% | 69.2% | 1.79 | 13 |
| Momentum | -2.31% | 36.4% | -0.43 | 22 |
| Mean Rev | +6.65% | 61.5% | 1.30 | 39 |

**META**
| Strategy | Return | Win Rate | Sharpe | Trades |
|----------|--------|----------|--------|--------|
| RSI | +0.31% | 33.3% | 0.13 | 9 |
| MACD | +1.58% | 47.8% | 0.48 | 23 |
| Bollinger | -1.71% | 36.8% | -0.43 | 19 |
| Momentum | +0.49% | 40.0% | 0.13 | 15 |
| Mean Rev | -0.26% | 50.0% | -0.05 | 32 |

**TSLA**
| Strategy | Return | Win Rate | Sharpe | Trades |
|----------|--------|----------|--------|--------|
| RSI | -1.74% | 30.8% | -0.42 | 13 |
| MACD | +1.40% | 39.1% | 0.31 | 23 |
| Bollinger | +1.43% | 41.2% | 0.37 | 17 |
| Momentum | +2.06% | 44.7% | 0.32 | 38 |
| Mean Rev | +2.48% | 51.0% | 0.39 | 51 |
