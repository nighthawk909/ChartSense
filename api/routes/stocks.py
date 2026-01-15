"""
Stock data routes - fetches data from Alpha Vantage
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.alpha_vantage import AlphaVantageService
from models.stock import StockQuote, StockHistory, TimeInterval

router = APIRouter()
av_service = AlphaVantageService()


@router.get("/quote/{symbol}", response_model=StockQuote)
async def get_stock_quote(symbol: str):
    """Get real-time quote for a stock symbol"""
    try:
        quote = await av_service.get_quote(symbol.upper())
        if not quote:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        return quote
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}", response_model=StockHistory)
async def get_stock_history(
    symbol: str,
    interval: TimeInterval = Query(default=TimeInterval.DAILY),
    outputsize: str = Query(default="compact", regex="^(compact|full)$"),
):
    """Get historical price data for a stock"""
    try:
        history = await av_service.get_history(
            symbol.upper(),
            interval=interval,
            outputsize=outputsize
        )
        if not history:
            raise HTTPException(status_code=404, detail=f"No history found for {symbol}")
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_symbols(query: str = Query(min_length=1)):
    """Search for stock symbols by keyword"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"Searching for: {query}")
        results = await av_service.search_symbols(query)
        logger.info(f"Search results: {len(results)} matches")
        return {"results": results}
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview/{symbol}")
async def get_company_overview(symbol: str):
    """Get company fundamentals and overview"""
    try:
        overview = await av_service.get_company_overview(symbol.upper())
        if not overview:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
