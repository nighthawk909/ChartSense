# CLAUDE.md - AI Assistant Context File

> This file provides context for AI assistants (Claude, GPT, Copilot, etc.) working on this codebase.

## Project Overview

**ChartSense** is a stock trading application focused on technical analysis with fundamental analysis support. It helps traders make informed decisions through chart analysis, technical indicators, and AI-powered insights.

### Key Value Proposition
- Technical analysis tools (RSI, MACD, Bollinger Bands, moving averages)
- Real-time and historical stock data via Alpha Vantage
- AI-powered pattern recognition and trade suggestions
- Watchlist and portfolio tracking
- Trade journaling for performance analysis

## Tech Stack

| Component | Technology |
|-----------|------------|
| Web App | React + TypeScript + Vite + Tailwind CSS |
| API Backend | FastAPI (Python) |
| Stock Data | Alpha Vantage API |
| Charts | TradingView Lightweight Charts / Recharts |
| Database | SQLite (dev) / PostgreSQL (prod) |
| AI/LLM | OpenAI GPT-4 (optional insights) |

## Project Structure

```
ChartSense/
├── apps/
│   └── web/                 # React web application
│       ├── src/
│       │   ├── components/  # Reusable UI components
│       │   │   ├── charts/  # Chart components
│       │   │   ├── indicators/ # Technical indicator displays
│       │   │   └── ui/      # Generic UI components
│       │   ├── pages/       # Route pages
│       │   ├── hooks/       # Custom React hooks
│       │   ├── services/    # API calls, data fetching
│       │   ├── types/       # TypeScript types
│       │   └── utils/       # Helper functions
│       └── public/
├── api/                     # FastAPI backend
│   ├── main.py              # API entry point
│   ├── routes/              # API endpoints
│   │   ├── stocks.py        # Stock data endpoints
│   │   ├── watchlist.py     # Watchlist management
│   │   └── analysis.py      # AI analysis endpoints
│   ├── services/            # Business logic
│   │   ├── alpha_vantage.py # Alpha Vantage integration
│   │   ├── indicators.py    # Technical indicator calculations
│   │   └── ai_analysis.py   # AI pattern recognition
│   ├── models/              # Pydantic models
│   └── database/            # SQLAlchemy models
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
└── tests/                   # Test suites
```

## Key Technical Concepts

### Technical Indicators to Support

1. **Trend Indicators**
   - Simple Moving Average (SMA)
   - Exponential Moving Average (EMA)
   - MACD (Moving Average Convergence Divergence)
   - ADX (Average Directional Index)

2. **Momentum Indicators**
   - RSI (Relative Strength Index)
   - Stochastic Oscillator
   - Williams %R
   - ROC (Rate of Change)

3. **Volatility Indicators**
   - Bollinger Bands
   - ATR (Average True Range)
   - Standard Deviation

4. **Volume Indicators**
   - OBV (On Balance Volume)
   - Volume SMA
   - VWAP (Volume Weighted Average Price)

### Fundamental Metrics to Display

- P/E Ratio (Price to Earnings)
- EPS (Earnings Per Share)
- Market Cap
- 52-Week High/Low
- Dividend Yield
- Revenue/Profit Growth

## Alpha Vantage API Usage

**Free Tier Limits**: 25 requests/day, 5 requests/minute

```python
# Example API calls
# Daily prices
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=YOUR_KEY

# Intraday prices
https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=YOUR_KEY

# Technical indicators (RSI)
https://www.alphavantage.co/query?function=RSI&symbol=IBM&interval=daily&time_period=14&series_type=close&apikey=YOUR_KEY

# Company overview (fundamentals)
https://www.alphavantage.co/query?function=OVERVIEW&symbol=IBM&apikey=YOUR_KEY
```

**Important**: Cache API responses aggressively due to rate limits!

## Common Tasks

### Running the Apps

```bash
# Web app (development)
cd apps/web
npm run dev

# API server
cd api
uvicorn main:app --reload --port 8000

# Run tests
pytest tests/
```

### Code Quality

```bash
# Frontend
cd apps/web
npm run lint
npm run format

# Backend
black api/
ruff check api/
```

## Architecture Decisions

1. **Web-first approach**: Focus on React web app for fastest iteration

2. **Backend for caching**: FastAPI backend caches Alpha Vantage responses to avoid rate limits

3. **Calculate indicators server-side**: Compute RSI, MACD, etc. in Python (numpy/pandas) for accuracy

4. **TradingView charts**: Use lightweight-charts for professional-looking stock charts

## Naming Conventions

**Files:**
- React components: PascalCase (`StockChart.tsx`, `WatchlistItem.tsx`)
- Hooks: camelCase with `use` prefix (`useStockData.ts`, `useIndicators.ts`)
- Services: camelCase (`alphaVantage.ts`, `stockService.ts`)
- Python: snake_case (`alpha_vantage.py`, `stock_routes.py`)

**Components:**
- PascalCase: `StockChart`, `IndicatorPanel`, `WatchlistCard`

**Functions:**
- camelCase (TypeScript): `fetchStockData()`, `calculateRSI()`
- snake_case (Python): `fetch_stock_data()`, `calculate_rsi()`

## Security Guidelines

- **Never expose API keys in frontend code**
- Store Alpha Vantage key in backend `.env` file
- Proxy all stock data requests through FastAPI backend
- Validate and sanitize all user inputs (stock symbols, etc.)

## Environment Variables

```env
# API Backend (.env)
ALPHA_VANTAGE_API_KEY=your_key_here
OPENAI_API_KEY=sk-...  # Optional, for AI insights
DATABASE_URL=sqlite:///./chartsense.db
SECRET_KEY=your_secret_key_for_jwt

# Web App (.env.local)
VITE_API_URL=http://localhost:8000
```

## UI Style Guide

### Colors (Trading Theme)

```typescript
// Bullish/Bearish
const GREEN = "#22c55e";  // Bullish, price up
const RED = "#ef4444";    // Bearish, price down

// Chart colors
const CHART_LINE = "#2563eb";  // Primary line color
const CHART_GRID = "#e5e7eb";  // Grid lines

// UI
const PRIMARY = "#2563eb";     // Primary actions
const SECONDARY = "#64748b";   // Secondary text
const BACKGROUND = "#f8fafc";  // Light background
const CARD_BG = "#ffffff";     // Card background
```

### Component Patterns

```tsx
// Stock price display with color coding
<span className={change >= 0 ? "text-green-500" : "text-red-500"}>
  {change >= 0 ? "+" : ""}{change.toFixed(2)}%
</span>

// Indicator value with status
<div className="flex items-center gap-2">
  <span>RSI:</span>
  <span className={rsi > 70 ? "text-red-500" : rsi < 30 ? "text-green-500" : "text-gray-600"}>
    {rsi.toFixed(2)}
  </span>
</div>
```

## Testing Requirements

- Unit tests for indicator calculations
- Integration tests for API endpoints
- Mock Alpha Vantage responses in tests
- Test edge cases (market closed, invalid symbols, etc.)

## Future Considerations

- WebSocket for real-time data (if upgrading from Alpha Vantage)
- Mobile app with React Native
- Paper trading simulation
- Backtesting engine
- Social features (share trade ideas)

---

## When Making Changes

1. **Before committing**: Run linters and tests
2. **Adding indicators**: Add calculation in `api/services/indicators.py`, display in React
3. **New API endpoints**: Add to `api/routes/`, update TypeScript types
4. **Caching**: Always cache Alpha Vantage responses (rate limits!)

---

# 🚨 STATE OF THE PROJECT (LIVE)

> **Last Updated**: 2026-01-16 (Updated with audit fixes)
> **Critical Status**: 4 Critical blockers addressed in this session

## Current Architecture

### Data Flow
```
┌─────────────────────────────────────────────────────────────────────┐
│                         CHARTSENSE ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   Frontend   │────▶│  FastAPI     │────▶│  Data APIs   │        │
│  │   (React)    │◀────│  Backend     │◀────│              │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│         │                    │                    │                 │
│         │              ┌─────┴─────┐              │                 │
│         │              │           │              │                 │
│         ▼              ▼           ▼              ▼                 │
│  ┌──────────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐          │
│  │ TradingView  │ │ SQLite │ │ Redis  │ │   Alpaca     │          │
│  │ Lightweight  │ │   DB   │ │ Cache  │ │   (Stocks)   │          │
│  │   Charts     │ └────────┘ └────────┘ └──────────────┘          │
│  └──────────────┘                        ┌──────────────┐          │
│                                          │   Binance    │          │
│                                          │   (Crypto)   │          │
│                                          └──────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

### Trading Bot Architecture
```
┌─────────────────────────────────────────────────────────────────────┐
│                        TRADING BOT FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    SCANNER LOOP (Async)                      │   │
│  │  ┌──────────────────┐     ┌──────────────────┐              │   │
│  │  │  Stock Scanner   │     │  Crypto Scanner  │              │   │
│  │  │  (Alpaca API)    │     │  (Binance API)   │              │   │
│  │  │  9:30AM-4PM EST  │     │  24/7 Operation  │              │   │
│  │  └────────┬─────────┘     └────────┬─────────┘              │   │
│  │           │                        │                         │   │
│  │           └──────────┬─────────────┘                         │   │
│  │                      ▼                                       │   │
│  │           ┌──────────────────┐                               │   │
│  │           │ Adaptive Engine  │                               │   │
│  │           │ (Scalp/Intra/    │                               │   │
│  │           │  Swing modes)    │                               │   │
│  │           └────────┬─────────┘                               │   │
│  │                    ▼                                         │   │
│  │           ┌──────────────────┐                               │   │
│  │           │  Signal Engine   │                               │   │
│  │           │  (RSI, MACD,     │                               │   │
│  │           │  Bollinger, etc) │                               │   │
│  │           └────────┬─────────┘                               │   │
│  │                    ▼                                         │   │
│  │           ┌──────────────────┐                               │   │
│  │           │ AI Confirmation  │                               │   │
│  │           │  (GPT-4 Review)  │                               │   │
│  │           └────────┬─────────┘                               │   │
│  │                    ▼                                         │   │
│  │           ┌──────────────────┐                               │   │
│  │           │ Execution Engine │◀──── ExecutionLogger          │   │
│  │           │ (Order Signing)  │                               │   │
│  │           └──────────────────┘                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## ✅ CRITICAL BLOCKERS (RESOLVED 2026-01-16)

### 1. Chart Desync Issue ✅ FIXED (2026-01-16)
- **Problem**: TradingView charts show stale data (days old on 1m timeframe)
- **Root Cause**: `StockChart.tsx` was using REST polling, not connected to WebSocket provider
- **Solution Implemented**:
  - `apps/web/src/components/StockChart.tsx` - **REWROTE** to integrate `useRealTimeData` hook
  - Added `hardReset()` function that triggers when data is >65 seconds stale
  - Shows WebSocket connection status indicator for intraday charts
  - Auto-detects stale data and prompts user to refresh
  - Calls `POST /api/stocks/force-refresh/{symbol}` on manual refresh
- **Status**: ✅ FIXED

### 2. Hybrid Scanning Sequential Execution ✅ FIXED
- **Problem**: Stock scanner waits for crypto scanner to finish
- **Root Cause**: Sequential loop instead of concurrent execution
- **Solution Implemented**:
  - `api/services/trading_bot.py:_main_loop()` - Rewritten with `asyncio.gather()`
  - Stock and Crypto scanners now run **truly in parallel**
  - Added `_run_aggressive_crypto_cycle()` for off-hours focus
- **Status**: ✅ FIXED

### 3. Silent Trade Execution Failures ✅ FIXED
- **Problem**: Bot generates signals but doesn't execute trades
- **Root Cause**: No logging of execution failures, symbol format mismatches
- **Solution Implemented**:
  - `api/services/execution_logger.py` - Centralized logger with specific error codes:
    - `[API_PERMISSION_ERROR]` - API key lacks trading permissions
    - `[INSUFFICIENT_FUNDS]` - Not enough buying power
    - `[ORDER_SIZE_TOO_SMALL]` - Below minimum notional value
    - `[SYMBOL_FORMAT_ERROR]` - Wrong symbol format (e.g., BTC/USD vs BTCUSD)
    - `[RATE_LIMIT_EXCEEDED]` - Too many API requests
    - `[MARKET_CLOSED]` - Trading during market hours only
  - `api/routes/bot.py` - New endpoints:
    - `GET /api/bot/diagnostic` - Full system diagnostic
    - `GET /api/bot/execution-errors` - Error summary and diagnosis
  - `api/services/crypto_service.py` - Enhanced symbol normalization
- **Status**: ✅ FIXED

## 📋 ACTIVE TODO LIST

### Core Execution & Hybrid Logic
- [x] **Fix Trade Execution**: Implemented `ExecutionLogger` with error codes ✅
  - `[API_PERMISSION_ERROR]` ✅
  - `[INSUFFICIENT_FUNDS]` ✅
  - `[ORDER_SIZE_TOO_SMALL]` ✅
  - `[SYMBOL_FORMAT_ERROR]` ✅
  - `[RATE_LIMIT_EXCEEDED]` ✅
- [x] **True Hybrid Scanning**: Parallel async workers for Crypto + Stocks ✅
- [ ] **Premarket Logic**: Enable scanning 4:00 AM – 9:30 AM EST

### Data & Chart Sync (TradingView)
- [x] **Real-Time Datafeed**: WebSocket `subscribeBars` implementation ✅
- [x] **ForceRefresh()**: Clear cache and fetch latest 100 candles ✅
- [x] **hardReset()**: Auto-triggers when chart data >65s behind ✅ (2026-01-16)
- [x] **StockChart WebSocket Integration**: Connected to `useRealTimeData` hook ✅ (2026-01-16)
- [ ] **Multi-Timeframe Validation**: Auto-sync 1m, 5m, 1d, 1w
- [ ] **Health Endpoint**: `/api/health` showing "Last Tick Received"

### UI/UX & Transparency
- [x] Clickable Insight Modals with calculation breakdown ✅
- [x] Performance Dashboard (PnL, Win Rate, Equity Curve) ✅
- [x] Adaptive Indicator Engine (Scalp/Intraday/Swing) ✅
- [x] Unified Markets tab with toggle ✅
- [x] Watchlist Promotion logic ✅
- [x] Dashboard page now uses PerformanceDashboard component ✅ (2026-01-16)
- [x] Dashboard Technical Indicators now fetch live data ✅ (2026-01-16)
- [x] Watchlist page now uses HybridWatchlist with AI carousel ✅ (2026-01-16)

### Diagnostic Tools
- [x] **Diagnostic Script**: Check all API connections ✅
  - `api/scripts/diagnostic.py` - Comprehensive system check
  - `GET /api/bot/diagnostic` - API endpoint for frontend
- [x] **Timestamp Validator**: Compare chart time vs system time ✅
  - Part of diagnostic script - validates 1m chart freshness
- [x] **Frontend Console Logging**: TradingBot page logs Start/Stop with diagnostics ✅ (2026-01-16)
  - Logs API URL, response time, error details
  - Auto-runs health check on failure
  - Look for `[TradingBot]` prefix in browser console

## 🧪 TESTING STANDARDS

### Before Marking Task "Done"
1. **Unit Test**: Write test for the specific function
2. **Integration Test**: Verify API endpoint works end-to-end
3. **Timestamp Validation**: Chart timestamp must match system time
4. **Console Check**: No 401/429 errors in browser console

### Test Commands
```bash
# Backend tests
cd api
pytest tests/ -v

# Specific test file
pytest tests/test_execution.py -v

# Frontend tests
cd apps/web
npm test

# Linting
cd api && ruff check .
cd apps/web && npm run lint
```

### Required Test Coverage
- `services/trading_bot.py` - Scanner loop tests
- `services/crypto_service.py` - Order execution tests
- `services/alpaca_service.py` - Stock order tests
- `services/indicators.py` - Calculation accuracy tests

## 🔧 GIT WORKFLOW

### Commit Message Format
```
<type>: <description>

Types:
- feat: New feature
- fix: Bug fix
- refactor: Code refactoring
- test: Adding tests
- docs: Documentation
- perf: Performance improvement

Examples:
- feat: implement websocket sync for 1m charts
- fix: parallel scanner execution for hybrid mode
- test: add execution logger validation tests
```

### Branch Strategy
```
main (production)
  └── develop (integration)
       ├── feature/websocket-charts
       ├── feature/parallel-scanner
       └── fix/execution-logger
```

### Pre-Commit Checklist
- [ ] Tests pass: `pytest tests/`
- [ ] Linting clean: `ruff check api/`
- [ ] No hardcoded API keys
- [ ] TypeScript builds: `npm run build`

## 📊 API ENDPOINTS REFERENCE

### Stock Data
- `GET /api/stocks/quote/{symbol}` - Current price
- `GET /api/stocks/history/{symbol}` - Historical OHLCV
- `GET /api/stocks/search` - Symbol search

### Analysis
- `GET /api/analysis/adaptive/{symbol}` - Adaptive indicators
- `GET /api/analysis/ai-insight/{symbol}` - AI analysis
- `POST /api/analysis/adaptive/mode` - Set trading mode

### Bot Control
- `POST /api/bot/start` - Start trading bot
- `POST /api/bot/stop` - Stop trading bot
- `GET /api/bot/status` - Bot status and positions
- `POST /api/bot/asset-class-mode` - Set hybrid mode

### Watchlist
- `GET /api/stocks-bot/watchlist` - Get watchlist
- `POST /api/stocks-bot/promotion/candidate` - Add candidate
- `GET /api/stocks-bot/promotion/candidates` - Get candidates

### Health & Diagnostics
- `GET /health` - Basic health check
- `GET /api/diagnostics/status` - Full system diagnostics (TO BE BUILT)

## 🔑 ENVIRONMENT VARIABLES

```env
# Required
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_PAPER=true

# Crypto (Optional)
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret

# Optional
OPENAI_API_KEY=sk-...
ALPHA_VANTAGE_API_KEY=your_key

# Database
DATABASE_URL=sqlite:///./chartsense.db
```

## ⚠️ COMMON PITFALLS

### Symbol Format Errors
```python
# WRONG - Will fail silently
crypto_symbol = "BTC/USDT"  # Some APIs use this
stock_symbol = "NASDAQ:AAPL"  # Some APIs use this

# CORRECT - Standardize
crypto_symbol = "BTCUSDT"  # Binance format
stock_symbol = "AAPL"  # Alpaca format
```

### Time Zone Issues
```python
# ALWAYS use UTC internally
from datetime import datetime, timezone
now = datetime.now(timezone.utc)

# Convert for display only
local_time = now.astimezone()
```

### Rate Limiting
```python
# Alpaca: 200 requests/minute
# Binance: 1200 requests/minute
# Alpha Vantage: 5 requests/minute

# Always implement backoff
import asyncio
async def rate_limited_request():
    try:
        return await make_request()
    except RateLimitError:
        await asyncio.sleep(60)
        return await make_request()
```

---

## 📍 DIAGNOSTIC QUESTIONS

If charts look stale, ask:
> "Print the last 5 logs from the WebSocket feed and current System.Time.
> If timestamps differ by >60 seconds, explain exactly why the Datafeed is lagging."

If trades aren't executing, ask:
> "Show me the ExecutionLogger output for the last 5 attempted trades.
> What specific error code was returned for each?"

If hybrid mode only scans crypto, ask:
> "Print the scanner loop timestamps for both Crypto and Stock workers.
> Are they running in parallel or sequentially?"

---

## 🔧 AUDIT FIX LOG (2026-01-16)

### Session Summary
Full audit and fix of 4 critical blockers identified in screenshots:
- Charts showing 14h/22h stale data
- "Unable to fetch bot status" error
- Missing Performance Dashboard and Watchlist modules

### Files Modified

#### 1. `apps/web/src/components/StockChart.tsx` - COMPLETE REWRITE
**Changes:**
- Integrated `useRealTimeData` hook for WebSocket real-time updates
- Added `hardReset()` function - triggers when data >65 seconds stale
- Added WebSocket connection status indicator (Wifi/WifiOff icons)
- Auto-calls `/api/stocks/force-refresh/{symbol}` on manual refresh
- New prop: `enableRealTime` (default: true for intraday intervals)
- Shows "Live" badge when WebSocket is streaming data

**Key Features:**
```typescript
// Stale detection - auto-triggers hardReset after 65 seconds
const STALE_THRESHOLD_SECONDS = 65

// WebSocket integration for intraday charts
const shouldUseRealTime = enableRealTime && isIntraday
const { latestBar, status: wsStatus, forceRefresh } = useRealTimeData(symbol)
```

#### 2. `apps/web/src/pages/Dashboard.tsx`
**Changes:**
- Added PerformanceDashboard component (collapsible via "Performance" button)
- Technical indicators now fetch live data from `/api/analysis/summary/{symbol}`
- Indicators update when selected stock changes

#### 3. `apps/web/src/pages/Watchlist.tsx` - COMPLETE REWRITE
**Changes:**
- Now uses HybridWatchlist component with AI Insights Carousel
- Added asset class toggle (All/Stocks/Crypto)
- Navigation to stock detail or crypto page based on symbol format

#### 4. `apps/web/src/pages/TradingBot.tsx`
**Changes:**
- Added comprehensive diagnostic logging to `handleStart()`
  - Logs: timestamp, API URL, current status, response time
  - On failure: runs health check and logs diagnosis
- Added diagnostic logging to `fetchStatus()`
  - Suggests `uvicorn main:app --reload --port 8000` if API unreachable

### How to Debug the "Unable to fetch bot status" Error

1. Open browser DevTools (F12) → Console tab
2. Click "Start Bot" button
3. Look for `[TradingBot]` log entries:
   ```
   [TradingBot] ========== START BOT INITIATED ==========
   [TradingBot] API URL: http://localhost:8000
   [TradingBot] DIAGNOSIS: API server appears to be offline
   [TradingBot] Cannot reach: http://localhost:8000/health
   ```

4. If you see "API server appears to be offline":
   ```bash
   cd api
   uvicorn main:app --reload --port 8000
   ```

### Verification Checklist
- [ ] Start the API server: `cd api && uvicorn main:app --reload`
- [ ] Start the web app: `cd apps/web && npm run dev`
- [ ] Open Dashboard → Select 1m interval → Should show "Live WebSocket Connected"
- [ ] Open Watchlist → Should show AI Insights Carousel
- [ ] Open Trading Bot → Click Start → Check console for diagnostic logs

---

## 🎯 SMR HYBRID IMPLEMENTATION (2026-01-16)

### Target Asset: SMR (NuScale Power Corp)
SMR is the primary test case for the Multi-Timeframe Analysis system. The AI must recognize that SMR may be:
- **Bullish on Daily** but **Bearish on 5-minute**
- **BUY for Scalping/Swing** but **HOLD for Long-term**

### Alexander Elder Triple Screen System

The system uses three "screens" across different timeframes:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TRIPLE SCREEN METHODOLOGY                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  SCREEN 1: THE TIDE (Daily - 9 months)                              │
│  └── Determines overall direction                                    │
│      • MACD Histogram slope                                          │
│      • 50/200 SMA (Golden/Death Cross)                              │
│      • ADX > 25 with +DI/-DI leadership                             │
│                                                                      │
│  SCREEN 2: THE WAVE (Hourly - 2 weeks)                              │
│  └── Identifies pullbacks for entry                                  │
│      • RSI < 40 in bullish tide = buy zone                          │
│      • Stochastic oversold = entry setup                            │
│      • EMA 9/21 cross                                               │
│                                                                      │
│  SCREEN 3: THE RIPPLE (5-Minute - 3 days)                           │
│  └── Precise entry timing                                            │
│      • RSI < 35 oversold = BUY trigger                              │
│      • MACD bullish cross                                           │
│      • Below VWAP = value entry                                     │
│      • Lower Bollinger Band = mean reversion                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### API Endpoints for SMR Analysis

```bash
# Triple Screen Analysis
GET /api/analysis/triple-screen/SMR

# Multi-Timeframe AI Insight
GET /api/analysis/ai-insight-multi/SMR

# Adaptive Indicators by Interval
GET /api/analysis/adaptive-indicators/SMR?interval=5min
GET /api/analysis/adaptive-indicators/SMR?interval=1day
```

### Adaptive Indicator Engine

**Short-Term/Intraday (1m, 5m, 15m):**
- Focus: Momentum & Breakouts
- Indicators: VWAP, ADX/DI crossovers, RSI (7-period), Bollinger Bands squeeze, Bull/Bear Flags

**Long-Term/Swing (1h, 1d, 1w):**
- Focus: Trend & Structure
- Indicators: 50/200 SMA, RSI (14-period), MACD, Volume Profile, Golden/Death Cross

### Frontend Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `MultiTimeframeInsight` | `apps/web/src/components/indicators/MultiTimeframeInsight.tsx` | Shows Scalp/Intraday/Swing/Long-term analysis |
| `TripleScreenPanel` | `apps/web/src/components/indicators/TripleScreenPanel.tsx` | Elder's Triple Screen System display |

### Stock Scanner Concurrent Execution

Stock and Crypto scanners now run **truly in parallel** using `asyncio.gather()`:

```python
# In trading_bot.py - _main_loop()
concurrent_tasks = []
if should_scan_stocks:
    concurrent_tasks.append(self._run_trading_cycle(extended_hours=False))
if should_scan_crypto:
    concurrent_tasks.append(self._run_crypto_cycle())

# Execute CONCURRENTLY - neither waits for the other
await asyncio.gather(*concurrent_tasks, return_exceptions=True)
```

### Diagnostic Question for Stock Scanner

If stock scanning appears idle while crypto is working:

> "Check the `asset_class_mode` in bot status. If set to 'crypto', stocks won't scan.
> Also verify `enabled_symbols` list is populated and market hours are active."

```bash
# Check bot configuration
curl http://localhost:8000/api/bot/status | jq '.asset_class_mode, .enabled_symbols'

# Verify market hours
curl http://localhost:8000/api/bot/status | jq '.stock_scan_progress'
```

### SMR Testing Checklist
- [ ] Navigate to `/stock/SMR` to view the stock detail page
- [ ] Verify Triple Screen Panel shows all three screens
- [ ] Check that Daily tide direction aligns with chart
- [ ] Verify 5-minute ripple indicators update with chart interval
- [ ] Test `/api/analysis/triple-screen/SMR` returns valid alignment score

---

## 🤖 HIERARCHICAL TRADING STRATEGY (2026-01-16)

### Philosophy: "Make Money Every Day"

The bot now implements an intelligent **Hierarchical Trading Strategy** that cascades through trading horizons to find opportunities:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HIERARCHICAL CASCADE LOGIC                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. SWING SCAN (First Priority)                                     │
│     └── Target: 5-15% gains over 2-10 days                          │
│         • RSI Period: 21 (less noise)                               │
│         • MACD: 19/39/9 (slower, fewer whipsaws)                    │
│         • Bollinger: 30 period, 2.5 std dev                         │
│         • Min R:R: 2.0                                              │
│         • Scan Interval: Hourly                                     │
│                                                                      │
│  2. INTRADAY SCAN (If no swing setups)                              │
│     └── Target: 1-3% gains within trading day                       │
│         • RSI Period: 14 (standard)                                 │
│         • MACD: 12/26/9 (standard)                                  │
│         • Bollinger: 20 period, 2.0 std dev                         │
│         • Min R:R: 1.5                                              │
│         • Scan Interval: Every 15 minutes                           │
│                                                                      │
│  3. SCALP SCAN (If no intraday setups)                              │
│     └── Target: 0.3-1% quick gains, 5-60 minutes                    │
│         • RSI Period: 7 (fast response)                             │
│         • MACD: 6/13/5 (very sensitive)                             │
│         • Bollinger: 10 period, 2.0 std dev                         │
│         • Min R:R: 1.2                                              │
│         • Scan Interval: Every 5 minutes                            │
│                                                                      │
│  → Goal: Find profitable opportunities EVERY trading day            │
└─────────────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Bot starts by looking for SWING trades** - These are the "big fish"
2. **If no swing opportunities found**, mark horizon as "exhausted" and cascade down
3. **Try INTRADAY trades** - Same-day, medium moves
4. **If nothing**, look for **SCALP opportunities** - Quick profits
5. **Reset exhausted flags periodically** (hourly for swing, 15min for intraday, 5min for scalp)

### Technical Indicators by Horizon

| Indicator | SWING | INTRADAY | SCALP |
|-----------|-------|----------|-------|
| RSI Period | 21 | 14 | 7 |
| MACD Fast/Slow/Signal | 19/39/9 | 12/26/9 | 6/13/5 |
| Bollinger Period | 30 | 20 | 10 |
| Bollinger Std Dev | 2.5 | 2.0 | 2.0 |
| ATR Period | 21 | 14 | 7 |
| Stop Loss (ATR multiplier) | 2.5x | 1.5x | 0.75x |
| Profit Target (ATR multiplier) | 4.0x | 2.5x | 1.5x |
| Max Hold Time | 7 days | 8 hours | 60 min |

### Opportunity Scoring

Each opportunity is scored on 5 components:

1. **Trend Score (25%)** - SMA alignment, Golden/Death Cross, ADX strength
2. **Momentum Score (25%)** - RSI, Stochastic, MACD crossover, ROC
3. **Pattern Score (20%)** - Bull/Bear Flags, H&S, Elliott Wave position
4. **Volume Score (15%)** - Volume ratio, OBV trend, VWAP position
5. **Multi-TF Score (15%)** - Alignment across timeframes

**Quality Ratings:**
- **EXCELLENT** (85+): Multiple confirmations, strong signal - TRADE
- **GOOD** (70-84): Solid setup - TRADE
- **FAIR** (55-69): Acceptable but risky - CONSIDER
- **POOR** (<55): Not recommended - SKIP

### Daily Goal Tracking

The bot tracks progress toward a daily profit goal (default 0.5%):

```json
{
  "date": "2026-01-16",
  "target_pct": 0.5,
  "achieved_pct": 0.35,
  "progress_pct": 70,
  "trades_taken": 3,
  "wins": 2,
  "losses": 1,
  "win_rate": 66.7,
  "horizons_used": ["SWING", "SCALP"]
}
```

### API Endpoints

```bash
# Get hierarchical strategy status
GET /api/bot/hierarchical/status

# Enable/disable hierarchical mode
POST /api/bot/hierarchical/toggle?enabled=true

# Set daily profit target
POST /api/bot/hierarchical/set-daily-target?target_pct=0.5

# Get all current opportunities
GET /api/bot/hierarchical/opportunities

# Force a specific horizon (override auto-cascade)
POST /api/bot/hierarchical/force-horizon?horizon=SCALP

# Get daily goal progress
GET /api/bot/hierarchical/daily-goal
```

### Key Files

| File | Purpose |
|------|---------|
| `api/services/hierarchical_strategy.py` | Core cascading logic, opportunity evaluation |
| `api/services/smart_scanner.py` | Orchestrates scans across horizons |
| `api/services/trading_bot.py` | Integration with main bot loop |
| `api/routes/bot.py` | API endpoints for hierarchical strategy |

### Elliott Wave Integration

The hierarchical strategy uses Elliott Wave analysis for pattern scoring:

- **Wave 3 position**: +25% bonus (strongest momentum)
- **Wave 5 position**: +20% bonus (final impulse)
- **Wave 1 position**: +15% bonus (early trend)
- **Wave 4 pullback**: +10% bonus (entry opportunity)
- **Corrective waves (A, C)**: +10% bonus (counter-trend plays)

### Diagnostic Questions

If the bot isn't finding opportunities:

> "Check `/api/bot/hierarchical/status` to see which horizons are exhausted.
> If all horizons show exhausted=true, the bot has scanned everything and
> found nothing meeting the quality thresholds."

If trades aren't executing despite opportunities:

> "Check the opportunity quality in `/api/bot/hierarchical/opportunities`.
> Only EXCELLENT and GOOD quality opportunities trigger trades.
> FAIR opportunities are logged but not executed automatically."
