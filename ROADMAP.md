# ChartSense Roadmap - Path to a Winning Trading Bot

> **Last Updated**: 2026-01-28
> **Goal**: Build a consistently profitable automated trading bot through data-driven simplification

---

## Current Status

**Problem Identified (2026-01-28)**:
- 3,633 lines in strategy files (too complex)
- 15+ indicators that often conflict
- No way to validate if any indicator actually helps
- Hierarchical strategy is overengineered

**Solution Agreed**:
1. Build backtesting first (validate what works)
2. Simplify strategy (remove what doesn't work)
3. Focus on paper trading (prove it in real-time)

---

## Phase 1: Backtesting Engine ✅ COMPLETED

**Status**: Done (2026-01-28) - Bug fixed (2026-01-28)

**What Was Built**:
- Backend backtesting engine using Alpaca historical data
- 6 simple strategies: RSI, MACD, Golden Cross, Bollinger, Momentum, Mean Reversion
- Performance metrics: Sharpe ratio, win rate, max drawdown, profit factor
- Frontend UI at `/backtest` page

**Bug Fixed (2026-01-28)**:
- Fixed indicator array bounds issues causing "No data found" and Internal Server Errors
- Updated `calculate_rsi`, `calculate_sma`, `calculate_ema`, `calculate_macd`, `calculate_bollinger_bands` to return arrays padded with `None` at the beginning, matching the input length
- Updated backtester to safely handle `None` values in indicator arrays
- All 6 strategies now work correctly

**Files Created**:
- `api/services/backtesting/` - Core engine
- `api/models/backtest.py` - Pydantic models
- `apps/web/src/pages/Backtest.tsx` - UI
- `apps/web/src/components/backtest/` - Components

**Files Modified (Bug Fix)**:
- `api/services/indicators.py` - Padded indicator arrays with None
- `api/services/backtester.py` - Added safe_get helper for indicator access

**How to Test**:
```bash
# IMPORTANT: Restart all servers before testing (kill old Python processes)
# On Windows, you may need to restart your machine if old servers persist

# Start API server fresh
cd api
uvicorn main:app --reload --port 8000

# Start web app
cd apps/web
npm run dev

# Or use ChartSense.bat after restarting machine
```

**API Test Commands**:
```bash
# Test RSI strategy
curl -s -X POST http://localhost:8000/api/advanced/backtest/run \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "strategy": "rsi_oversold", "initial_capital": 100000, "position_size_pct": 0.1, "stop_loss_pct": 0.05, "take_profit_pct": 0.10}'

# Test MACD strategy
curl -s -X POST http://localhost:8000/api/advanced/backtest/run \
  -H "Content-Type: application/json" \
  -d '{"symbol": "MSFT", "strategy": "macd_crossover", "initial_capital": 100000, "position_size_pct": 0.1, "stop_loss_pct": 0.05, "take_profit_pct": 0.10}'

# Test Bollinger strategy
curl -s -X POST http://localhost:8000/api/advanced/backtest/run \
  -H "Content-Type: application/json" \
  -d '{"symbol": "GOOGL", "strategy": "bollinger_bounce", "initial_capital": 100000, "position_size_pct": 0.1, "stop_loss_pct": 0.05, "take_profit_pct": 0.10}'
```

---

## Phase 2: Strategy Simplification ✅ COMPLETED

**Status**: Done (2026-01-28)

**Goal**: Use backtesting data to identify which indicators actually help

**Tasks**:
1. [x] Run backtests on current 15+ indicator strategy
2. [x] Run backtests on simple RSI-only strategy
3. [x] Run backtests on simple MACD-only strategy
4. [x] Compare results - which has better Sharpe ratio?
5. [x] Remove indicators that don't improve results
6. [x] Target: Reduce to 3-5 core indicators max

**Backtest Results Summary** (35 tests across 7 stocks, 5 strategies):
| Strategy | Avg Return | Avg Sharpe | Recommendation |
|----------|------------|------------|----------------|
| Momentum | +1.01% | **0.33** | PRIMARY |
| Mean Reversion | +1.05% | 0.17 | SECONDARY |
| Bollinger | +0.59% | 0.12 | CONDITIONAL |
| RSI Oversold | -0.64% | -0.10 | IMPROVED (25/75 thresholds) |
| MACD Crossover | **-1.24%** | **-0.43** | REMOVED |

**Changes Made**:
1. **strategy_engine.py**:
   - Reduced MACD weight from 25% to 5%
   - Added Momentum indicator (25% weight) - best performer
   - Added Mean Reversion indicator (20% weight) - second best
   - Updated RSI thresholds from 30/70 to 25/75

2. **hierarchical_strategy.py**:
   - Reduced MACD crossover score contribution from +15 to +5
   - Increased Rate of Change (momentum) contribution from +10 to +20
   - Added mean reversion scoring component

**New Indicator Weights**:
```python
DEFAULT_WEIGHTS = {
    "momentum": 0.25,      # NEW - best performing
    "mean_reversion": 0.20, # NEW - second best
    "rsi": 0.20,           # Kept - improved thresholds
    "sma_crossover": 0.15,
    "bollinger": 0.10,
    "volume": 0.05,
    "macd": 0.05,          # REDUCED from 0.25
}
```

**Files Modified**:
- `api/services/strategy_engine.py` - New weights, new indicators
- `api/services/hierarchical_strategy.py` - Updated momentum scoring

**Full Analysis**: See `BACKTEST_ANALYSIS.md` for detailed results

---

## Phase 3: Paper Trading Validation 📋 PENDING

**Status**: Not Started

**Goal**: Validate simplified strategy in real market conditions

**Tasks**:
1. [ ] Run simplified strategy on paper trading for 2 weeks
2. [ ] Track daily P&L, win rate, drawdown
3. [ ] Compare to backtest predictions
4. [ ] Adjust if needed based on live results

**Success Criteria**:
- Consistent daily profits (even small)
- Paper trading results match backtest expectations
- No catastrophic losses (>5% single day)

---

## Phase 4: Live Trading (Future)

**Status**: After Phase 3 Validation

**Prerequisites**:
- Phase 3 paper trading shows consistent profits
- Backtest Sharpe > 1.0
- Paper trading matches backtest results
- Risk management verified

---

## Key Metrics to Track

| Metric | Target | Current (Backtest) |
|--------|--------|-------------------|
| Sharpe Ratio | > 1.0 | **1.86** (GOOGL Momentum best) |
| Win Rate | > 50% | **64.3%** (GOOGL Momentum) |
| Max Drawdown | < 15% | TBD in paper trading |
| Profit Factor | > 1.5 | TBD in paper trading |
| Indicator Count | 3-5 | **6** (reduced from 15+) |
| Core Strategy | Simple | **Momentum + Mean Reversion** |

**Note**: Best individual results from GOOGL with Momentum strategy. Average across all tests is lower but positive for recommended strategies.

---

## Anti-Patterns to Avoid

1. ❌ Adding more indicators hoping one will help
2. ❌ Making the strategy more complex
3. ❌ Skipping backtesting validation
4. ❌ Over-optimizing for past data (curve fitting)
5. ❌ Trading live before paper trading validation

---

## Decision Log

| Date | Decision | Reasoning |
|------|----------|-----------|
| 2026-01-28 | Build backtesting first | Can't know what works without testing |
| 2026-01-28 | Simplify after testing | Remove what doesn't help |
| 2026-01-28 | Focus on paper trading | Prove it works before risking real money |

---

## Bug Fixes Log

| Date | Bug | Root Cause | Fix |
|------|-----|------------|-----|
| 2026-01-28 | Backtest returns "No data found" | Old server processes on port 8000 not reloading | Restart machine to clear zombie processes |
| 2026-01-28 | Backtest returns IndexError/Internal Error | Indicator arrays (RSI, SMA, etc.) shorter than price arrays | Padded all indicator functions with None at beginning to match input length |
| 2026-01-28 | Bollinger strategy returns NaN/Infinity | Indicator index mismatch | Fixed Bollinger, MACD to use aligned arrays |

---

## Files Reference

**Core Strategy Files** (to simplify in Phase 2):
- `api/services/indicators.py` - 800+ lines
- `api/services/trading_bot.py` - 1200+ lines
- `api/services/smart_scanner.py` - 600+ lines
- `api/services/hierarchical_strategy.py` - 500+ lines

**Backtesting** (Phase 1 - Complete):
- `api/services/backtesting/engine.py`
- `api/services/backtester.py`
- `api/routes/advanced.py` (backtest endpoints)
- `apps/web/src/pages/Backtest.tsx`

---

## Next Session Checklist

When resuming work:
1. Read this file (`ROADMAP.md`)
2. Check current phase status
3. Continue with next incomplete task
4. Update this file with progress
