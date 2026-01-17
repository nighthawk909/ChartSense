# ChartSense Deployment Links

## Live Deployment
- **Vercel App**: https://chart-sense-virid.vercel.app

## Repository
- **GitHub**: https://github.com/nighthawk909/ChartSense

## Latest Commit
- **Hash**: f20a502
- **Message**: fix: Remove unused variables to fix Vercel build

## Features in This Release

### Tactical Control Bar
- Emergency Close All (2-click confirmation)
- Pause New Entries toggle
- Strategy Override dropdown (Conservative/Moderate/Aggressive)

### Priority Tier System for Smart Scanning
- Tier 1 (HIGH): 3-second scans for high volatility/news
- Tier 2 (STANDARD): 30-second scans for normal watchlist
- Tier 3 (LOW): 3-minute scans for consolidating symbols

### Strategy Labels
- Added SCALP and INTRADAY to TradeType enum
- Time horizon badges on AI Decision cards

### UI Components
- Asset Class Toggle (Crypto/Stocks/Both)
- AI Intelligence Sidebar with Decisions/Analysis/Scan tabs
- Ticker Carousel with quick-flip navigation
- Confidence Score Reasoning Modal with weight breakdown

### New API Endpoints
- POST /api/bot/pause-entries
- POST /api/bot/strategy-override
- POST /api/bot/emergency-close-all
- GET /api/bot/priority-tiers
- GET /api/bot/execution-log
- GET /api/bot/strong-buy-trace
