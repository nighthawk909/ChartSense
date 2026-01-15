"""
ChartSense API - FastAPI Backend
Technical analysis stock trading app with automated trading bot
"""
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables BEFORE other imports
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import stocks, watchlist, analysis
from routes import bot, positions, performance, settings
from routes import ai, watchlist_bot
from routes import crypto, advanced
from database.connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

