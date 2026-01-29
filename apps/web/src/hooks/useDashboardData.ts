import { useState, useEffect, useCallback } from 'react'
import { getSymbolName } from '../utils/dashboard-helpers'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface StockQuote {
  symbol: string
  price: number
  change: number
  change_percent: number
}

export interface WatchlistStock {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  isPosition?: boolean
  unrealizedPnl?: number
  unrealizedPnlPct?: number
}

export interface Position {
  symbol: string
  current_price: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  trade_type?: string
}

export interface TechnicalIndicators {
  rsi_14: { value: number; signal: string }
  macd: { value: number; signal: string }
  sma_20: { value: number; signal: string }
  sma_50: { value: number; signal: string }
  bollinger?: { position: string; signal: string }
}

export type TimeInterval = '1min' | '5min' | '15min' | '30min' | '60min' | 'daily'

// Fallback watchlist stocks (used when no positions exist)
export const fallbackWatchlist: WatchlistStock[] = [
  { symbol: 'AAPL', name: 'Apple Inc.', price: 0, change: 0, changePercent: 0 },
  { symbol: 'MSFT', name: 'Microsoft Corp.', price: 0, change: 0, changePercent: 0 },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 0, change: 0, changePercent: 0 },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 0, change: 0, changePercent: 0 },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', price: 0, change: 0, changePercent: 0 },
]

export const marketIndices = [
  { symbol: 'SPY', name: 'S&P 500' },
  { symbol: 'QQQ', name: 'Nasdaq 100' },
  { symbol: 'DIA', name: 'Dow Jones' },
]

export const intervals: { value: TimeInterval; label: string }[] = [
  { value: '1min', label: '1m' },
  { value: '5min', label: '5m' },
  { value: '15min', label: '15m' },
  { value: '60min', label: '1h' },
  { value: 'daily', label: '1D' },
]

export const periods = ['1D', '1W', '1M', '3M', '1Y', 'ALL']

export interface UseDashboardDataReturn {
  // Selection state
  selectedStock: string
  setSelectedStock: (stock: string) => void
  selectedPeriod: string
  setSelectedPeriod: (period: string) => void
  selectedInterval: TimeInterval
  setSelectedInterval: (interval: TimeInterval) => void

  // Data state
  watchlist: WatchlistStock[]
  positions: Position[]
  indices: Record<string, StockQuote>
  indicators: TechnicalIndicators | null

  // UI state
  lastUpdated: Date | null
  loading: boolean
  error: string | null
  refreshing: boolean
  indicatorsLoading: boolean
  showPerformance: boolean
  setShowPerformance: (show: boolean) => void

  // Actions
  handleRefresh: () => void
}

export function useDashboardData(): UseDashboardDataReturn {
  const [selectedStock, setSelectedStock] = useState('AAPL')
  const [selectedPeriod, setSelectedPeriod] = useState('1M')
  const [selectedInterval, setSelectedInterval] = useState<TimeInterval>('daily')
  const [watchlist, setWatchlist] = useState<WatchlistStock[]>(fallbackWatchlist)
  const [positions, setPositions] = useState<Position[]>([])
  const [indices, setIndices] = useState<Record<string, StockQuote>>({})
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [indicators, setIndicators] = useState<TechnicalIndicators | null>(null)
  const [indicatorsLoading, setIndicatorsLoading] = useState(false)
  const [showPerformance, setShowPerformance] = useState(false)

  // Fetch current positions from trading bot
  const fetchPositions = useCallback(async (): Promise<Position[]> => {
    try {
      const response = await fetch(`${API_URL}/api/positions/current`)
      if (response.ok) {
        const data = await response.json()
        return data.positions || []
      }
    } catch (err) {
      console.error('Failed to fetch positions:', err)
    }
    return []
  }, [])

  // Fetch live stock quotes - now prioritizes positions
  const fetchQuotes = useCallback(async () => {
    setError(null)
    try {
      // Fetch positions first - these take priority in the watchlist
      const currentPositions = await fetchPositions()
      setPositions(currentPositions)

      // Fetch index quotes
      const indexPromises = marketIndices.map(async (idx) => {
        const response = await fetch(`${API_URL}/api/stocks/quote/${idx.symbol}`)
        if (response.ok) {
          const data = await response.json()
          return { symbol: idx.symbol, data }
        }
        return null
      })

      // Build watchlist: positions first, then fill with fallback stocks
      const positionSymbols = new Set(currentPositions.map(p => p.symbol))

      // Convert positions to watchlist format
      const positionWatchlist: WatchlistStock[] = currentPositions.map(p => ({
        symbol: p.symbol,
        name: getSymbolName(p.symbol),
        price: p.current_price,
        change: 0,
        changePercent: 0,
        isPosition: true,
        unrealizedPnl: p.unrealized_pnl,
        unrealizedPnlPct: p.unrealized_pnl_pct,
      }))

      // Get remaining slots for fallback stocks (max 5 total)
      const remainingSlots = Math.max(0, 5 - positionWatchlist.length)
      const additionalStocks = fallbackWatchlist
        .filter(s => !positionSymbols.has(s.symbol))
        .slice(0, remainingSlots)

      // Combine and fetch quotes for all
      const allWatchlistStocks = [...positionWatchlist, ...additionalStocks]

      const watchlistPromises = allWatchlistStocks.map(async (stock) => {
        try {
          const response = await fetch(`${API_URL}/api/stocks/quote/${stock.symbol}`)
          if (response.ok) {
            const data = await response.json()
            return {
              ...stock,
              price: data.price || stock.price,
              change: data.change || 0,
              changePercent: data.change_percent || 0
            }
          }
        } catch {
          // Skip failed quotes
        }
        return stock
      })

      const [indexResults, watchlistResults] = await Promise.all([
        Promise.all(indexPromises),
        Promise.all(watchlistPromises)
      ])

      // Update indices
      const newIndices: Record<string, StockQuote> = {}
      indexResults.forEach((result) => {
        if (result) {
          newIndices[result.symbol] = result.data
        }
      })
      setIndices(newIndices)

      // Update watchlist
      setWatchlist(watchlistResults)

      // Auto-select first position if we have positions and current selection isn't a position
      if (currentPositions.length > 0 && !positionSymbols.has(selectedStock)) {
        setSelectedStock(currentPositions[0].symbol)
      }

      setLastUpdated(new Date())
    } catch (err) {
      console.error('Failed to fetch quotes:', err)
      setError('Failed to fetch live data. Make sure the API is running.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [fetchPositions, selectedStock])

  // Fetch technical indicators for selected stock
  const fetchIndicators = useCallback(async (symbol: string) => {
    setIndicatorsLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/analysis/summary/${symbol}`)
      if (response.ok) {
        const data = await response.json()
        setIndicators(data.indicators)
      }
    } catch (err) {
      console.error('Failed to fetch indicators:', err)
    } finally {
      setIndicatorsLoading(false)
    }
  }, [])

  // Initial fetch and auto-refresh
  useEffect(() => {
    fetchQuotes()
    // Refresh every 30 seconds
    const interval = setInterval(fetchQuotes, 30000)
    return () => clearInterval(interval)
  }, [fetchQuotes])

  // Fetch indicators when selected stock changes
  useEffect(() => {
    fetchIndicators(selectedStock)
  }, [selectedStock, fetchIndicators])

  const handleRefresh = useCallback(() => {
    setRefreshing(true)
    fetchQuotes()
    fetchIndicators(selectedStock)
  }, [fetchQuotes, fetchIndicators, selectedStock])

  return {
    selectedStock,
    setSelectedStock,
    selectedPeriod,
    setSelectedPeriod,
    selectedInterval,
    setSelectedInterval,
    watchlist,
    positions,
    indices,
    indicators,
    lastUpdated,
    loading,
    error,
    refreshing,
    indicatorsLoading,
    showPerformance,
    setShowPerformance,
    handleRefresh,
  }
}
