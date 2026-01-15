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
