import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, RefreshCw, AlertCircle, BarChart3 } from 'lucide-react'
import StockChart from '../components/StockChart'
import PerformanceDashboard from '../components/dashboard/PerformanceDashboard'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface StockQuote {
  symbol: string
  price: number
  change: number
  change_percent: number
}

interface WatchlistStock {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
}

interface TechnicalIndicators {
  rsi_14: { value: number; signal: string }
  macd: { value: number; signal: string }
  sma_20: { value: number; signal: string }
  sma_50: { value: number; signal: string }
  bollinger?: { position: string; signal: string }
}

// Default watchlist (will be updated with live data)
const defaultWatchlist: WatchlistStock[] = [
  { symbol: 'AAPL', name: 'Apple Inc.', price: 0, change: 0, changePercent: 0 },
  { symbol: 'MSFT', name: 'Microsoft Corp.', price: 0, change: 0, changePercent: 0 },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 0, change: 0, changePercent: 0 },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 0, change: 0, changePercent: 0 },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', price: 0, change: 0, changePercent: 0 },
]

const marketIndices = [
  { symbol: 'SPY', name: 'S&P 500' },
  { symbol: 'QQQ', name: 'Nasdaq 100' },
  { symbol: 'DIA', name: 'Dow Jones' },
]

type TimeInterval = '1min' | '5min' | '15min' | '30min' | '60min' | 'daily'

export default function Dashboard() {
  const [selectedStock, setSelectedStock] = useState('AAPL')
  const [selectedPeriod, setSelectedPeriod] = useState('1M')
  const [selectedInterval, setSelectedInterval] = useState<TimeInterval>('daily')
  const [watchlist, setWatchlist] = useState<WatchlistStock[]>(defaultWatchlist)
  const [indices, setIndices] = useState<Record<string, StockQuote>>({})
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [indicators, setIndicators] = useState<TechnicalIndicators | null>(null)
  const [indicatorsLoading, setIndicatorsLoading] = useState(false)
  const [showPerformance, setShowPerformance] = useState(false)

  // Fetch live stock quotes
  const fetchQuotes = async () => {
    setError(null)
    try {
      // Fetch index quotes
      const indexPromises = marketIndices.map(async (idx) => {
        const response = await fetch(`${API_URL}/api/stocks/quote/${idx.symbol}`)
        if (response.ok) {
          const data = await response.json()
          return { symbol: idx.symbol, data }
        }
        return null
      })

      // Fetch watchlist quotes
      const watchlistPromises = defaultWatchlist.map(async (stock) => {
        const response = await fetch(`${API_URL}/api/stocks/quote/${stock.symbol}`)
        if (response.ok) {
          const data = await response.json()
          return { ...stock, price: data.price, change: data.change, changePercent: data.change_percent }
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
      setLastUpdated(new Date())
    } catch (err) {
      console.error('Failed to fetch quotes:', err)
      setError('Failed to fetch live data. Make sure the API is running.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  // Fetch technical indicators for selected stock
  const fetchIndicators = async (symbol: string) => {
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
  }

  // Initial fetch and auto-refresh
  useEffect(() => {
    fetchQuotes()
    // Refresh every 30 seconds
    const interval = setInterval(fetchQuotes, 30000)
    return () => clearInterval(interval)
  }, [])

  // Fetch indicators when selected stock changes
  useEffect(() => {
    fetchIndicators(selectedStock)
  }, [selectedStock])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchQuotes()
    fetchIndicators(selectedStock)
  }

  // Available intervals with labels
  const intervals: { value: TimeInterval; label: string }[] = [
    { value: '1min', label: '1m' },
    { value: '5min', label: '5m' },
    { value: '15min', label: '15m' },
    { value: '60min', label: '1h' },
    { value: 'daily', label: '1D' },
  ]

  const periods = ['1D', '1W', '1M', '3M', '1Y', 'ALL']

  return (
    <div className="space-y-6">
      {/* Header with timestamp and refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <div className="flex items-center gap-3 mt-1">
            {lastUpdated && (
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                <span className="text-sm text-green-400">
                  Live data updated: {lastUpdated.toLocaleTimeString()}
                </span>
              </div>
            )}
            {loading && (
              <span className="text-sm text-slate-400">Loading...</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPerformance(!showPerformance)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              showPerformance ? 'bg-blue-600 text-white' : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            Performance
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Performance Dashboard (collapsible) */}
      {showPerformance && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <PerformanceDashboard compact />
        </div>
      )}

      {/* Market Overview */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Market Overview</h2>
        <div className="grid grid-cols-3 gap-4">
          {marketIndices.map((idx) => {
            const quote = indices[idx.symbol]
            return (
              <div
                key={idx.symbol}
                className="bg-slate-800 rounded-lg p-4 border border-slate-700"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-400">{idx.name}</p>
                    <p className="text-xl font-semibold">
                      {quote ? `$${quote.price.toFixed(2)}` : '--'}
                    </p>
                  </div>
                  {quote && (
                    <div
                      className={`flex items-center gap-1 ${
                        quote.change_percent >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}
                    >
                      {quote.change_percent >= 0 ? (
                        <TrendingUp className="h-4 w-4" />
                      ) : (
                        <TrendingDown className="h-4 w-4" />
                      )}
                      <span className="font-medium">
                        {quote.change_percent >= 0 ? '+' : ''}
                        {quote.change_percent.toFixed(2)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <div className="grid grid-cols-3 gap-6">
        {/* Chart */}
        <div className="col-span-2">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-4">
              <h2 className="text-lg font-semibold">{selectedStock} Chart</h2>
              <div className="flex flex-wrap gap-2 sm:gap-4">
                {/* Interval selector */}
                <div className="flex flex-wrap gap-1 bg-slate-900 rounded-lg p-1">
                  {intervals.map((int) => (
                    <button
                      key={int.value}
                      onClick={() => setSelectedInterval(int.value)}
                      className={`px-2 py-1 text-xs rounded transition-colors whitespace-nowrap ${
                        selectedInterval === int.value
                          ? 'bg-blue-600 text-white'
                          : 'text-slate-400 hover:text-white hover:bg-slate-700'
                      }`}
                    >
                      {int.label}
                    </button>
                  ))}
                </div>
                {/* Period selector */}
                <div className="flex flex-wrap gap-1">
                  {periods.map((period) => (
                    <button
                      key={period}
                      onClick={() => setSelectedPeriod(period)}
                      className={`px-2 sm:px-3 py-1 text-xs sm:text-sm rounded transition-colors whitespace-nowrap ${
                        selectedPeriod === period
                          ? 'bg-slate-600 text-white'
                          : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                      }`}
                    >
                      {period}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="h-96">
              <StockChart
                symbol={selectedStock}
                period={selectedPeriod}
                interval={selectedInterval}
                enableRealTime={true}
              />
            </div>
          </div>
        </div>

        {/* Watchlist */}
        <div>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Watchlist</h2>
              <Link
                to="/watchlist"
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                View All
              </Link>
            </div>
            <div className="space-y-2">
              {watchlist.map((stock) => (
                <button
                  key={stock.symbol}
                  onClick={() => setSelectedStock(stock.symbol)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                    selectedStock === stock.symbol
                      ? 'bg-blue-600/20 border border-blue-500'
                      : 'hover:bg-slate-700'
                  }`}
                >
                  <div className="text-left">
                    <p className="font-medium">{stock.symbol}</p>
                    <p className="text-sm text-slate-400">{stock.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">
                      {stock.price > 0 ? `$${stock.price.toFixed(2)}` : '--'}
                    </p>
                    <p
                      className={`text-sm ${
                        stock.changePercent >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}
                    >
                      {stock.price > 0 ? (
                        <>
                          {stock.changePercent >= 0 ? '+' : ''}
                          {stock.changePercent.toFixed(2)}%
                        </>
                      ) : '--'}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Technical Indicators - Now fetching live data */}
      <section>
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Technical Indicators - {selectedStock}</h2>
            {indicatorsLoading && (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <RefreshCw className="w-4 h-4 animate-spin" />
                Loading...
              </div>
            )}
          </div>
          <div className="grid grid-cols-4 gap-4">
            <IndicatorCard
              name="RSI (14)"
              value={indicators?.rsi_14?.value ?? '--'}
              status={indicators?.rsi_14?.signal ?? 'Loading'}
              statusColor={getStatusColor(indicators?.rsi_14?.signal)}
            />
            <IndicatorCard
              name="MACD"
              value={indicators?.macd?.value ?? '--'}
              status={indicators?.macd?.signal ?? 'Loading'}
              statusColor={getStatusColor(indicators?.macd?.signal)}
            />
            <IndicatorCard
              name="SMA (50)"
              value={indicators?.sma_50?.value ?? '--'}
              status={indicators?.sma_50?.signal ?? 'Loading'}
              statusColor={getStatusColor(indicators?.sma_50?.signal)}
            />
            <IndicatorCard
              name="Bollinger Bands"
              value={indicators?.bollinger?.position ?? 'Middle'}
              status={indicators?.bollinger?.signal ?? 'Neutral'}
              statusColor={getStatusColor(indicators?.bollinger?.signal)}
            />
          </div>
        </div>
      </section>
    </div>
  )
}

function getStatusColor(signal?: string): string {
  if (!signal) return 'text-slate-400'
  const lowerSignal = signal.toLowerCase()
  if (lowerSignal.includes('bullish') || lowerSignal.includes('oversold') || lowerSignal.includes('above')) {
    return 'text-green-500'
  }
  if (lowerSignal.includes('bearish') || lowerSignal.includes('overbought') || lowerSignal.includes('below')) {
    return 'text-red-500'
  }
  return 'text-yellow-500'
}

function IndicatorCard({
  name,
  value,
  status,
  statusColor,
}: {
  name: string
  value: number | string
  status: string
  statusColor: string
}) {
  return (
    <div className="bg-slate-700/50 rounded-lg p-4">
      <p className="text-sm text-slate-400 mb-1">{name}</p>
      <p className="text-xl font-semibold">
        {typeof value === 'number' ? value.toFixed(2) : value}
      </p>
      <p className={`text-sm ${statusColor}`}>{status}</p>
    </div>
  )
}
