# ChartSense Deployment Guide

## Quick Deploy

### Option 1: Vercel + Railway (Recommended)

**Frontend (Vercel) - FREE**
1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click "New Project" → Import your repo
3. Set root directory to `apps/web`
4. Add environment variable: `VITE_API_URL=https://your-railway-url.up.railway.app`
5. Deploy!

**Backend (Railway) - $5/month**
1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click "New Project" → Deploy from GitHub repo
3. Set root directory to `api`
4. Add environment variables:
   - `ALPACA_API_KEY` - Your Alpaca API key
   - `ALPACA_SECRET_KEY` - Your Alpaca secret key
   - `ALPACA_TRADING_MODE` - Set to `paper` for testing
   - `OPENAI_API_KEY` - (Optional) For AI features
   - `ALPHA_VANTAGE_API_KEY` - (Optional) For fundamentals
5. Deploy!

### Option 2: Render (Alternative)

**Backend (Render) - FREE tier available**
1. Go to [render.com](https://render.com)
2. New Web Service → Connect GitHub
3. Root directory: `api`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables (same as Railway)

---

## Environment Variables Required

| Variable | Required | Description |
|----------|----------|-------------|
| `ALPACA_API_KEY` | Yes | Alpaca trading API key |
| `ALPACA_SECRET_KEY` | Yes | Alpaca trading secret |
| `ALPACA_TRADING_MODE` | Yes | `paper` or `live` |
| `OPENAI_API_KEY` | No | Enables AI stock discovery |
| `ALPHA_VANTAGE_API_KEY` | No | Company fundamentals |
| `DATABASE_URL` | Auto | PostgreSQL URL (Railway auto-injects) |
| `ALLOWED_ORIGINS` | No | Additional CORS origins (comma-separated) |
| `SECRET_KEY` | Yes | Random string for security |

---

## Database Persistence (IMPORTANT)

**Your trades persist automatically when using Railway/Render:**

1. **Railway**: Click "New" > "Database" > "PostgreSQL" in your project
   - Railway auto-injects `DATABASE_URL` - no config needed!

2. **Render**: Add PostgreSQL from Dashboard > "New" > "PostgreSQL"
   - Copy connection string to `DATABASE_URL` env var

3. **Alternative Cloud DBs** (if hosting elsewhere):
   - Supabase: Free PostgreSQL at [supabase.com](https://supabase.com)
   - Neon: Free PostgreSQL at [neon.tech](https://neon.tech)

**What gets saved:**
- All executed trades with entry/exit prices
- Open positions with stop-loss/take-profit levels
- Performance metrics (win rate, P&L, Sharpe ratio)
- Bot configuration and settings

---

## After Deployment

1. Update Vercel with your Railway backend URL
2. Test the connection at `https://your-app.vercel.app`
3. Enable paper trading to test
4. Once confirmed working, switch to live if desired

---

## Running the Bot 24/7

The bot runs automatically when the backend is deployed:
- **Stocks**: Trades during market hours (9:30 AM - 4:00 PM ET)
- **Crypto**: Trades 24/7 (when enabled in settings)
- **Extended Hours**: Pre-market and after-hours with limit orders

The Railway/Render server stays running continuously, so your bot never sleeps!
