"""
ChartSense API - FastAPI Backend
Technical analysis stock trading app with automated trading bot
Updated: 2026-01-28 - Fixed backtesting indicator bounds issue
"""
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables BEFORE other imports
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import stocks, watchlist, analysis
from routes import bot, positions, performance, settings
from routes import ai, watchlist_bot
from routes import crypto, advanced, notifications, backtest
from database.connection import init_db

# Configure structured logging with correlation IDs
from services.logging_config import (
    setup_logging,
    get_logger,
    CorrelationIdMiddleware
)

# Use JSON logging in production (when not in debug mode)
use_json_logging = os.getenv("LOG_FORMAT", "console").lower() == "json"
setup_logging(use_json=use_json_logging)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    # Startup
    logger.info("Initializing database...")
    init_db()
    logger.info("ChartSense API starting up")
    yield
    # Shutdown
    logger.info("ChartSense API shutting down")


app = FastAPI(
    title="ChartSense API",
    description="Technical analysis stock trading API with automated trading bot",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware - supports env var ALLOWED_ORIGINS for production
default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://chart-sense-virid.vercel.app",
    "https://chart-sense.vercel.app",
]
# Add any custom origins from environment variable
custom_origins = os.getenv("ALLOWED_ORIGINS", "")
if custom_origins:
    default_origins.extend([o.strip() for o in custom_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID middleware for request tracing
app.add_middleware(CorrelationIdMiddleware)

# Include routers - Market Data
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])

# Include routers - Trading Bot
app.include_router(bot.router, prefix="/api/bot", tags=["bot"])
app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
app.include_router(performance.router, prefix="/api/performance", tags=["performance"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

# Include routers - AI Advisor
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])

# Include routers - User Stocks & Repository
app.include_router(watchlist_bot.router, prefix="/api/stocks-bot", tags=["stocks-bot"])

# Include routers - Crypto Trading (24/7)
app.include_router(crypto.router, prefix="/api/crypto", tags=["crypto"])

# Include routers - Advanced Analysis
app.include_router(advanced.router, prefix="/api/advanced", tags=["advanced"])

# Include routers - Notifications
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])

# Include routers - Backtesting
app.include_router(backtest.router)


@app.get("/")
async def root():
    return {"message": "ChartSense API", "version": "0.3.0", "features": [
        "Stock Trading Bot",
        "24/7 Crypto Trading",
        "Multi-Timeframe Analysis",
        "Pattern Recognition",
        "Sentiment Analysis",
        "Backtesting Engine",
        "Risk Management",
    ]}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

