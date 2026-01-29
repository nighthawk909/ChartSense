# ChartSense Feature Registry

> **Living document** - Update this file whenever features are added, modified, or removed.
> **Last Updated**: 2026-01-17

---

## Quick Reference

| Category | Count |
|----------|-------|
| Pages | 10 |
| Components | 25+ |
| API Endpoints | 80+ |
| Bot Controls | 12 |
| Chart Types | 3 |

---

## 1. PAGES

### Landing Page (`/`)
**File**: `apps/web/src/pages/Landing.tsx`

| Element | Type | Action |
|---------|------|--------|
| "Launch App" button | Button | Navigate to `/dashboard` |
| "Trading Bot" button | Button | Navigate to `/bot` |
| GitHub link | Link | External |

**Sections**: Hero, Features (3-column), Security, CTA, Footer

---

### Dashboard (`/dashboard`)
**File**: `apps/web/src/pages/Dashboard.tsx`

| Element | Type | Action |
|---------|------|--------|
| Performance toggle | Button | Show/hide PerformanceDashboard |
| Refresh button | Button | Refresh quotes and indicators |
| Interval buttons | ButtonGroup | 1m, 5m, 15m, 1h, 1D |
| Period buttons | ButtonGroup | 1D, 1W, 1M, 3M, 1Y, ALL |
| Watchlist symbols | Clickable | Select stock for chart |

**API Calls**:
- `GET /api/stocks/quote/{symbol}`
- `GET /api/analysis/summary/{symbol}`

**Displays**:
- [ ] Market indices (S&P 500, Nasdaq, Dow Jones)
- [ ] Stock chart with volume
- [ ] Watchlist with prices
- [ ] Technical indicators (RSI, MACD, SMA, Bollinger)

---

### Stock Detail (`/stock/:symbol`) - **UNIFIED FOR STOCKS AND CRYPTO**
**File**: `apps/web/src/pages/StockDetail.tsx`

> **Note**: As of 2026-01-17, this page handles BOTH stocks and crypto symbols.
> Crypto symbols (e.g., `BTC/USD`, `BTCUSD`) are automatically detected and use
> appropriate crypto endpoints while showing the same full technical analysis.

| Element | Type | Action |
|---------|------|--------|
| Bitcoin icon | Display | Shows only for crypto symbols |
| CRYPTO badge | Badge | Shows "CRYPTO" tag for crypto symbols |
| Star button | Toggle | Add/remove from watchlist |
| Refresh button | Button | Refresh all data |
| Interval selector | ButtonGroup | 1m, 5m, 15m, 30m, 1h, 1D |
| Period selector | ButtonGroup | 1D, 1W, 1M, 3M, 1Y, ALL |
| Chart type toggle | Toggle | Candlestick/Line |

**API Calls (Stock)**:
- `GET /api/stocks/quote/{symbol}`
- `GET /api/analysis/rsi/{symbol}`
- `GET /api/analysis/macd/{symbol}`
- `GET /api/analysis/sma/{symbol}`
- `GET /api/advanced/support-resistance/{symbol}`
- `GET /api/advanced/elliott-wave/{symbol}`
- `GET /api/advanced/trend-lines/{symbol}`
- `GET /api/analysis/ai-insight/{symbol}`

**API Calls (Crypto)**:
- `GET /api/crypto/quote/{symbol}`
- Analysis endpoints use normalized symbol (BTCUSD format)

**Components**:
- [x] StockChart / CryptoChart (auto-detects)
- [x] PatternInsights
- [x] MultiTimeframeInsight
- [x] TripleScreenPanel
- [x] AdaptiveIndicatorPanel

---

### Watchlist (`/watchlist`)
**File**: `apps/web/src/pages/Watchlist.tsx`

| Element | Type | Action |
|---------|------|--------|
| Asset toggle | ButtonGroup | All, Stocks, Crypto |
| Add Symbol button | Button | Open add modal |
| Search input | Input | Search symbols |
| Popular stocks | Buttons | Quick-add AAPL, MSFT, etc. |
| Popular crypto | Buttons | Quick-add BTC, ETH, etc. |
| Symbol rows | Clickable | Navigate to detail page |

**API Calls**:
- `GET /api/stocks/search?query={query}`
- `POST /api/watchlist/add`
- `DELETE /api/watchlist/remove/{symbol}`

**Components**:
- [ ] HybridWatchlist with AI carousel
- [ ] Add Symbol Modal

---

### Trading Bot (`/bot`)
**File**: `apps/web/src/pages/TradingBot.tsx`

| Element | Type | Action |
|---------|------|--------|
| Start button | Button | `POST /api/bot/start` |
| Stop button | Button | `POST /api/bot/stop` |
| Pause button | Button | `POST /api/bot/pause` |
| Resume button | Button | `POST /api/bot/resume` |
| Refresh button | Button | Refresh all data |
| AI Panel toggle | Button | Toggle sidebar |
| Asset toggle | ButtonGroup | both, stocks, crypto |
| Emergency Close | Button | `POST /api/bot/emergency-close-all` |
| Pause Entries | Toggle | `POST /api/bot/pause-entries` |
| Strategy dropdown | Select | Conservative/Moderate/Aggressive |
| Auto Trade toggle | Toggle | `POST /api/bot/auto-trade` |
| Close Position | Button | Per position row |

**API Calls**:
- `GET /api/bot/status`
- `GET /api/positions/account`
- `GET /api/positions/current`
- `GET /api/performance/metrics`
- `GET /api/performance/trades`
- `GET /api/bot/activity`
- `POST /api/bot/asset-class-mode`

**Components**:
- [ ] BotStatusCard
- [ ] BotControls
- [ ] AccountSummary
- [ ] CurrentPositions
- [ ] TradeHistory
- [ ] PerformanceStats
- [ ] ActivityLog
- [ ] TickerCarousel
- [ ] AIIntelligenceSidebar

---

### Markets (`/markets`)
**File**: `apps/web/src/pages/Markets.tsx`

| Element | Type | Action |
|---------|------|--------|
| Asset toggle | ButtonGroup | Stocks, Crypto, Hybrid |
| Discover button | Button | `GET /api/analysis/recommendations` |
| Refresh button | Button | Refresh status |
| Period selector | ButtonGroup | Today, 1W, 1M |
| Auto Trade button | Button | `POST /api/bot/auto-trade-opportunities` |
| BUY button | Button | Per opportunity |
| Close chart | Button | Close preview |

**API Calls**:
- `GET /api/bot/status`
- `GET /api/bot/scan-progress`
- `GET /api/analysis/top-movers`
- `GET /api/analysis/recommendations`
- `POST /api/bot/asset-class-mode`
- `POST /api/bot/execute-opportunity`
- `POST /api/bot/auto-trade-opportunities`

---

### Crypto (`/crypto`)
**File**: `apps/web/src/pages/Crypto.tsx`

| Element | Type | Action |
|---------|------|--------|
| Crypto buttons | ButtonGroup | BTC, ETH, SOL, DOGE, etc. |
| Refresh button | Button | Refresh quotes |
| Timeframe selector | ButtonGroup | 1m, 5m, 15m, 1h, 1D |

**API Calls**:
- `GET /api/crypto/market-status`
- `GET /api/crypto/quote/{symbol}`

---

### Analysis History (`/analysis-history`)
**File**: `apps/web/src/pages/AnalysisHistory.tsx`

| Element | Type | Action |
|---------|------|--------|
| Execution log | List | View past signals |
| AI decisions | List | View AI reasoning |

**API Calls**:
- `GET /api/bot/execution-log`
- `GET /api/bot/status`

---

### Settings (`/settings`)
**File**: `apps/web/src/pages/Settings.tsx`

| Element | Type | Action |
|---------|------|--------|
| Risk settings | Inputs | Configure risk params |
| Position sizing | Input | Set max position % |
| Presets | Buttons | Apply preset configs |
| Reset button | Button | Reset to defaults |
| Save button | Button | Save settings |

**API Calls**:
- `GET /api/settings/`
- `PUT /api/settings/`
- `POST /api/settings/reset`
- `GET /api/settings/presets`
- `POST /api/settings/presets/{name}`

---

### Backtesting (`/backtest`) - **NEW 2026-01-28**
**File**: `apps/web/src/pages/Backtest.tsx`

| Element | Type | Action |
|---------|------|--------|
| Strategy selector | Buttons | Select RSI, MACD, etc. |
| Symbol selector | Buttons + Input | Select AAPL, MSFT, or custom |
| Initial Capital | Input | Set starting capital |
| Position Size % | Input | Set position sizing |
| Stop Loss % | Input | Set stop loss |
| Take Profit % | Input | Set take profit |
| Run Backtest | Button | `POST /api/advanced/backtest/run` |

**API Calls**:
- `GET /api/advanced/backtest/strategies`
- `POST /api/advanced/backtest/run`

**Displays**:
- [x] Performance summary (total return, final capital)
- [x] Key metrics (win rate, Sharpe, profit factor, drawdown)
- [x] Trade statistics (avg win, avg loss, largest trades)
- [x] Backtest period dates

---

## 2. COMPONENTS

### Chart Components

| Component | File | Purpose |
|-----------|------|---------|
| StockChart | `components/StockChart.tsx` | TradingView stock chart with WebSocket |
| CryptoChart | `components/CryptoChart.tsx` | Crypto chart display |
| CryptoSelector | `components/CryptoSelector.tsx` | Crypto symbol dropdown |

**StockChart Features**:
- [ ] Candlestick/Line modes
- [ ] Volume histogram
- [ ] Real-time WebSocket updates
- [ ] Stale data detection (>65s)
- [ ] Connection status indicator
- [ ] Manual refresh button
- [ ] Period/interval controls

---

### Bot Components

| Component | File | Purpose |
|-----------|------|---------|
| BotControls | `components/bot/BotControls.tsx` | Tactical control bar |
| BotStatusCard | `components/bot/BotStatusCard.tsx` | Status display |
| AccountSummary | `components/bot/AccountSummary.tsx` | Account info |
| CurrentPositions | `components/bot/CurrentPositions.tsx` | Open positions |
| TradeHistory | `components/bot/TradeHistory.tsx` | Trade history |
| PerformanceStats | `components/bot/PerformanceStats.tsx` | Performance metrics |
| ActivityLog | `components/bot/ActivityLog.tsx` | Event log |
| TickerCarousel | `components/bot/TickerCarousel.tsx` | Active trades carousel |
| AssetClassToggle | `components/bot/AssetClassToggle.tsx` | Asset mode toggle |
| AIIntelligenceSidebar | `components/bot/AIIntelligenceSidebar.tsx` | AI decisions sidebar |
| ConfidenceReasoningModal | `components/bot/ConfidenceReasoningModal.tsx` | AI reasoning modal |

---

### Indicator Components

| Component | File | Purpose |
|-----------|------|---------|
| AdaptiveIndicatorPanel | `components/indicators/AdaptiveIndicatorPanel.tsx` | Mode-based indicators |
| MultiTimeframeInsight | `components/indicators/MultiTimeframeInsight.tsx` | Multi-TF analysis |
| PatternInsights | `components/indicators/PatternInsights.tsx` | Pattern detection |
| TripleScreenPanel | `components/indicators/TripleScreenPanel.tsx` | Elder's Triple Screen |

---

### Watchlist Components

| Component | File | Purpose |
|-----------|------|---------|
| HybridWatchlist | `components/watchlist/HybridWatchlist.tsx` | Advanced watchlist with AI |

---

### Dashboard Components

| Component | File | Purpose |
|-----------|------|---------|
| PerformanceDashboard | `components/dashboard/PerformanceDashboard.tsx` | Performance analytics |

---

### Layout Components

| Component | File | Purpose |
|-----------|------|---------|
| Layout | `components/Layout.tsx` | Main app layout with nav |
| ErrorBoundary | `components/ErrorBoundary.tsx` | Error handling wrapper |

---

## 3. API ENDPOINTS

### Stock Data (`/api/stocks/`)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/quote/{symbol}` | GET | Real-time quote | ✅ |
| `/history/{symbol}` | GET | Historical OHLCV | ✅ |
| `/search` | GET | Search symbols | ✅ |
| `/overview/{symbol}` | GET | Company fundamentals | ✅ |
| `/force-refresh/{symbol}` | POST | Clear cache | ✅ |
| `/data-source-status` | GET | API status | ✅ |

---

### Crypto (`/api/crypto/`)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/supported` | GET | Supported pairs | ✅ |
| `/quote/{symbol}` | GET | Crypto quote | ✅ |
| `/quotes` | GET | Multiple quotes | ✅ |
| `/bars/{symbol}` | GET | Historical bars | ✅ |
| `/analyze/{symbol}` | GET | Technical analysis | ✅ |
| `/patterns/{symbol}` | GET | Pattern detection | ✅ |
| `/market-status` | GET | Market status | ✅ |
| `/positions` | GET | Crypto positions | ✅ |
| `/order` | POST | Place order | ✅ |
| `/position/{symbol}` | DELETE | Close position | ✅ |

---

### Analysis (`/api/analysis/`)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/rsi/{symbol}` | GET | RSI indicator | ✅ |
| `/macd/{symbol}` | GET | MACD indicator | ✅ |
| `/sma/{symbol}` | GET | Moving average | ✅ |
| `/summary/{symbol}` | GET | All indicators | ✅ |
| `/ai-insight/{symbol}` | GET | AI insight | ✅ |
| `/ai-insight-multi/{symbol}` | GET | Multi-TF insight | ✅ |
| `/triple-screen/{symbol}` | GET | Triple Screen | ✅ |
| `/adaptive-indicators/{symbol}` | GET | Adaptive indicators | ✅ |
| `/recommendations` | GET | Buy recommendations | ✅ |
| `/top-movers` | GET | Top gainers/losers | ✅ |

---

### Advanced (`/api/advanced/`)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/patterns/{symbol}` | GET | Pattern detection | ✅ |
| `/elliott-wave/{symbol}` | GET | Elliott Wave | ✅ |
| `/support-resistance/{symbol}` | GET | S/R levels | ✅ |
| `/trend-lines/{symbol}` | GET | Trend lines | ✅ |
| `/sentiment/{symbol}` | GET | Sentiment | ✅ |
| `/backtest/strategies` | GET | Backtest strategies | ✅ |
| `/backtest/run` | POST | Run backtest | ✅ |

---

### Bot (`/api/bot/`)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/status` | GET | Bot status | ✅ |
| `/start` | POST | Start bot | ✅ |
| `/stop` | POST | Stop bot | ✅ |
| `/pause` | POST | Pause bot | ✅ |
| `/resume` | POST | Resume bot | ✅ |
| `/health` | GET | Health check | ✅ |
| `/execution-log` | GET | Execution log | ✅ |
| `/pause-entries` | POST | Toggle pause entries | ✅ |
| `/strategy-override` | POST | Set strategy | ✅ |
| `/auto-trade` | POST | Toggle auto-trade | ✅ |
| `/emergency-close-all` | POST | Emergency close | ✅ |
| `/asset-class-mode` | POST | Set hybrid mode | ✅ |
| `/scan-progress` | GET | Scan progress | ✅ |
| `/activity` | GET | Activity stream | ✅ |
| `/diagnostic` | GET | System diagnostic | ✅ |
| `/hierarchical/status` | GET | Hierarchical status | ✅ |
| `/hierarchical/toggle` | POST | Toggle hierarchical | ✅ |
| `/execute-opportunity` | POST | Execute trade | ✅ |
| `/auto-trade-opportunities` | POST | Auto-execute | ✅ |

---

### Positions (`/api/positions/`)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/account` | GET | Account summary | ✅ |
| `/current` | GET | Open positions | ✅ |
| `/{symbol}` | GET | Position details | ✅ |
| `/close/{symbol}` | POST | Close position | ✅ |
| `/close-all` | POST | Close all | ✅ |

---

### Performance (`/api/performance/`)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/summary` | GET | Performance summary | ✅ |
| `/metrics` | GET | Metrics | ✅ |
| `/equity-curve` | GET | Equity curve | ✅ |
| `/trades` | GET | Trade history | ✅ |
| `/trades/{id}` | GET | Trade details | ✅ |
| `/trades/{id}/analysis` | GET | Trade analysis | ✅ |
| `/daily-summary` | GET | Daily summary | ✅ |
| `/weekly-report` | GET | Weekly report | ✅ |

---

### Watchlist (`/api/watchlist/`)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/` | GET | Get watchlist | ✅ |
| `/add` | POST | Add symbol | ✅ |
| `/remove/{symbol}` | DELETE | Remove symbol | ✅ |
| `/check/{symbol}` | GET | Check if watched | ✅ |

---

### Settings (`/api/settings/`)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/` | GET | Get settings | ✅ |
| `/` | PUT | Update settings | ✅ |
| `/reset` | POST | Reset defaults | ✅ |
| `/presets` | GET | Get presets | ✅ |
| `/presets/{name}` | POST | Apply preset | ✅ |

---

## 4. TESTING CHECKLIST

> **Last Test Run**: 2026-01-17
> **Test Method**: API endpoint testing via curl, bot control testing

### API Endpoint Test Results

| Category | Endpoint | Status | Notes |
|----------|----------|--------|-------|
| Stocks | `/api/stocks/quote/AAPL` | ✅ PASS | Returns price data |
| Stocks | `/api/stocks/search?query=apple` | ✅ PASS | Returns search results |
| Stocks | `/api/stocks/history/AAPL` | ✅ PASS | Returns OHLCV data |
| Crypto | `/api/crypto/supported` | ✅ PASS | Returns supported pairs |
| Crypto | `/api/crypto/quote/BTCUSD` | ✅ PASS | Returns BTC price |
| Crypto | `/api/crypto/market-status` | ✅ PASS | Returns market open |
| Analysis | `/api/analysis/rsi/AAPL` | ⚠️ FAIL | Enum conversion issue - fix applied |
| Analysis | `/api/analysis/macd/AAPL` | ✅ PASS | Returns MACD values |
| Analysis | `/api/analysis/summary/AAPL` | ⚠️ FAIL | Pydantic validation - fix applied |
| Analysis | `/api/analysis/ai-insight/AAPL` | ✅ PASS | Returns AI insight |
| Bot | `/api/bot/status` | ✅ PASS | Returns bot state |
| Bot | `/api/bot/health` | ✅ PASS | Returns healthy |
| Bot | `/api/bot/execution-log` | ✅ PASS | Returns log |
| Bot | `/api/bot/scan-progress` | ✅ PASS | Returns progress |
| Positions | `/api/positions/account` | ✅ PASS | Returns account info |
| Positions | `/api/positions/current` | ✅ PASS | Returns positions |
| Performance | `/api/performance/summary` | ✅ PASS | Returns summary |
| Performance | `/api/performance/metrics` | ✅ PASS | Returns metrics |
| Watchlist | `/api/watchlist/` | ✅ PASS | Returns watchlist |
| Settings | `/api/settings/` | ✅ PASS | Returns settings |
| Settings | `/api/settings/presets` | ✅ PASS | Returns presets |
| Advanced | `/api/advanced/patterns/AAPL` | ✅ PASS | Returns patterns |
| Advanced | `/api/advanced/support-resistance/AAPL` | ✅ PASS | Returns S/R levels |
| Advanced | `/api/advanced/elliott-wave/AAPL` | ✅ PASS | Returns Elliott Wave |

### Bot Controls Test (API)
- [x] Start button works - `POST /api/bot/start` → `{"success":true,"state":"RUNNING"}`
- [x] Stop button works - `POST /api/bot/stop` → `{"success":true,"state":"STOPPED"}`
- [x] Pause button works - `POST /api/bot/pause` → `{"success":true,"state":"PAUSED"}`
- [x] Resume button works - `POST /api/bot/resume` → `{"success":true,"state":"RUNNING"}`

### Watchlist Test (API)
- [x] Add symbol works - `POST /api/watchlist/add` → Success
- [x] Get watchlist works - `GET /api/watchlist/` → Returns 11 symbols
- [x] Remove symbol works - `DELETE /api/watchlist/remove/TSLA` → Success

### Pages Load Test
- [ ] Landing page loads
- [ ] Dashboard loads with market data
- [ ] Stock detail loads for any symbol
- [ ] Watchlist loads with symbols
- [ ] Trading Bot page loads
- [ ] Markets page loads
- [ ] Crypto page loads
- [ ] Analysis History loads
- [ ] Settings page loads

### Navigation Test
- [ ] All sidebar links work
- [ ] Landing → Dashboard works
- [ ] Landing → Bot works
- [ ] Watchlist → Stock Detail works
- [ ] Markets → Symbol detail works
- [ ] Back button works everywhere

### Chart Test
- [ ] Candlestick chart renders
- [ ] Line chart renders
- [ ] Volume bars display
- [ ] Interval change works (1m, 5m, etc.)
- [ ] Period change works (1D, 1W, etc.)
- [ ] Real-time updates work (1m chart)
- [ ] Refresh button works
- [ ] Connection status shows correctly

### Data Display Test
- [ ] Prices update correctly
- [ ] Percentage changes are accurate
- [ ] Colors are correct (green/red)
- [ ] Technical indicators display
- [ ] AI insights display
- [ ] Patterns detected display

### Mobile Responsive Test
- [ ] Dashboard responsive on mobile
- [ ] Trading Bot responsive on mobile
- [ ] Stock Detail responsive on mobile
- [ ] Navigation menu works on mobile
- [ ] Carousel swipe works on mobile

### Error Handling Test
- [ ] ErrorBoundary catches crashes
- [ ] API errors show message
- [ ] Network errors handled
- [ ] Loading states display

---

## 5. KNOWN ISSUES

| Issue | Status | Notes |
|-------|--------|-------|
| Crypto signals above threshold not auto-buying | By Design | AI gate must APPROVE + auto_trade_mode must be ON |
| "AI WAIT" showing for crypto | Working | AI is saying to wait for better entry conditions |

### Bot Auto-Buy Logic Explained

The bot uses a **3-gate system** before executing a trade:

1. **Threshold Gate**: Confidence must be >= threshold (65% for crypto, 70% for stocks)
2. **AI Gate**: AI must respond with "APPROVE" (not "WAIT" or "REJECT")
3. **Auto Trade Gate**: `auto_trade_mode` must be `true`

If you see "AI WAIT" for a symbol above threshold (like AAVE at 78%), it means:
- Gate 1 passed (78% > 65%)
- Gate 2 blocked (AI said WAIT, not APPROVE)
- The AI has concerns and is waiting for better entry conditions

To see why AI is waiting, check the execution log in Activity tab.

---

## 6. FUTURE FEATURES

| Feature | Priority | Status |
|---------|----------|--------|
| Paper trading simulation | High | Planned |
| Push notifications | Medium | Planned |
| Social trading | Low | Backlog |
| Backtesting UI | Medium | ✅ DONE (2026-01-28) |
| Strategy Simplification | High | Next (see ROADMAP.md) |

---

## 7. VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 0.3.0 | 2026-01-17 | Unified crypto/stock detail page, fixed hold time display, improved Performance panel layout |
| 0.2.0 | 2026-01-17 | Added ErrorBoundary, fixed botApi production URL |
| 0.1.0 | 2026-01-16 | Initial feature registry |

### Version 0.3.0 Changes (2026-01-17)

**Unified Crypto/Stock Detail Page**:
- Crypto symbols now navigate to `/stock/{symbol}` instead of `/crypto`
- StockDetail.tsx detects crypto symbols and uses appropriate endpoints
- Full technical analysis (Elliott Wave, Triple Screen, Patterns) available for crypto
- Bitcoin icon and "CRYPTO" badge shown for crypto symbols
- 24/7 trading label for crypto (vs "Trading day" for stocks)

**Fixed Position Hold Time Display**:
- Fixed bug showing "20471d 0h" for positions
- Now shows "N/A" for invalid dates (epoch 0, future dates)
- Properly handles positions < 365 days old
- Shows minutes for positions < 1 hour

**Improved Performance Panel Layout**:
- Changed from 4-column to 2x2 grid layout
- Labels no longer truncated (Win Rate, Total P&L, etc.)
- Larger text for values (text-2xl)
- Better padding and spacing
