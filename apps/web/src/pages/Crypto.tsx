import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, RefreshCw, AlertCircle, Activity, DollarSign, Clock } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface CryptoQuote {
  symbol: string
  price: number
  change_24h: number
  change_percent_24h: number
  high_24h: number
  low_24h: number
  volume_24h: number
  market_cap?: number
}

interface MarketStatus {
  market_open: boolean
  message: string
}

const POPULAR_CRYPTOS = [
  { symbol: 'BTC/USD', name: 'Bitcoin', icon: '₿' },
  { symbol: 'ETH/USD', name: 'Ethereum', icon: 'Ξ' },
  { symbol: 'SOL/USD', name: 'Solana', icon: '◎' },
  { symbol: 'DOGE/USD', name: 'Dogecoin', icon: 'Ð' },
  { symbol: 'XRP/USD', name: 'Ripple', icon: '✕' },
  { symbol: 'ADA/USD', name: 'Cardano', icon: '₳' },
  { symbol: 'AVAX/USD', name: 'Avalanche', icon: 'A' },
  { symbol: 'MATIC/USD', name: 'Polygon', icon: 'M' },
]

export default function Crypto() {
  const [quotes, setQuotes] = useState<Record<string, CryptoQuote>>({})
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null)
  const [selectedCrypto, setSelectedCrypto] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchMarketStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/crypto/market-status`)
      if (response.ok) {
        const data = await response.json()
        setMarketStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch market status:', err)
    }
  }

  const fetchQuote = async (symbol: string): Promise<CryptoQuote | null> => {
    try {
      const response = await fetch(`${API_URL}/api/crypto/quote/${encodeURIComponent(symbol)}`)
      if (response.ok) {
        return await response.json()
      }
    } catch (err) {
      console.error(`Failed to fetch quote for ${symbol}:`, err)
    }
    return null
  }

  const fetchAllQuotes = async () => {
    setError(null)
    const newQuotes: Record<string, CryptoQuote> = {}

    // Fetch quotes in parallel
    const results = await Promise.allSettled(
      POPULAR_CRYPTOS.map(async (crypto) => {
        const quote = await fetchQuote(crypto.symbol)
        if (quote) {
          return { symbol: crypto.symbol, quote }
        }
        return null
      })
    )

    results.forEach((result) => {
      if (result.status === 'fulfilled' && result.value) {
        newQuotes[result.value.symbol] = result.value.quote
      }
    })

    if (Object.keys(newQuotes).length === 0) {
      setError('Unable to fetch crypto prices. Make sure the API is running and Alpaca credentials are configured.')
    } else {
      setLastUpdated(new Date())
    }

    setQuotes(newQuotes)
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchAllQuotes()
    setRefreshing(false)
  }

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await Promise.all([fetchMarketStatus(), fetchAllQuotes()])
      setLoading(false)
    }
    init()

    // Refresh every 30 seconds
    const interval = setInterval(fetchAllQuotes, 30000)
    return () => clearInterval(interval)
  }, [])

  const formatPrice = (price: number) => {
    if (price >= 1000) return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    if (price >= 1) return price.toFixed(2)
    return price.toFixed(4)
  }

  const formatVolume = (volume: number) => {
    if (volume >= 1e9) return `$${(volume / 1e9).toFixed(2)}B`
    if (volume >= 1e6) return `$${(volume / 1e6).toFixed(2)}M`
    if (volume >= 1e3) return `$${(volume / 1e3).toFixed(2)}K`
    return `$${volume.toFixed(2)}`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Cryptocurrency</h1>
          <div className="flex items-center gap-3">
            <p className="text-slate-400">24/7 crypto markets via Alpaca</p>
            {lastUpdated && (
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                <span className="text-xs text-green-400">
                  Updated {lastUpdated.toLocaleTimeString()}
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4">
          {marketStatus && (
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
              marketStatus.market_open ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
            }`}>
              <Activity className="h-4 w-4" />
              {marketStatus.market_open ? 'Market Open' : 'Market Closed'}
            </div>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Crypto Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {POPULAR_CRYPTOS.map((crypto) => {
          const quote = quotes[crypto.symbol]
          const isSelected = selectedCrypto === crypto.symbol

          return (
            <button
              key={crypto.symbol}
              onClick={() => setSelectedCrypto(isSelected ? null : crypto.symbol)}
              className={`bg-slate-800 rounded-lg p-4 border transition-all text-left ${
                isSelected ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-slate-700 hover:border-slate-600'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{crypto.icon}</span>
                  <div>
                    <p className="font-semibold">{crypto.name}</p>
                    <p className="text-xs text-slate-400">{crypto.symbol}</p>
                  </div>
                </div>
                {quote && (
                  <div className={`flex items-center gap-1 text-sm ${
                    quote.change_percent_24h >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}>
                    {quote.change_percent_24h >= 0 ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : (
                      <TrendingDown className="h-4 w-4" />
                    )}
                    {quote.change_percent_24h >= 0 ? '+' : ''}
                    {quote.change_percent_24h?.toFixed(2)}%
                  </div>
                )}
              </div>

              {quote ? (
                <div>
                  <p className="text-2xl font-bold">${formatPrice(quote.price)}</p>
                  <p className={`text-sm ${quote.change_24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {quote.change_24h >= 0 ? '+' : ''}${formatPrice(Math.abs(quote.change_24h))} today
                  </p>
                </div>
              ) : (
                <div className="h-14 flex items-center justify-center">
                  <RefreshCw className="h-5 w-5 animate-spin text-slate-500" />
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* Selected Crypto Details */}
      {selectedCrypto && quotes[selectedCrypto] && (
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h2 className="text-lg font-semibold mb-4">
            {POPULAR_CRYPTOS.find(c => c.symbol === selectedCrypto)?.name} Details
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
                <DollarSign className="h-4 w-4" />
                24h High
              </div>
              <p className="text-lg font-semibold text-green-500">
                ${formatPrice(quotes[selectedCrypto].high_24h)}
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
                <DollarSign className="h-4 w-4" />
                24h Low
              </div>
              <p className="text-lg font-semibold text-red-500">
                ${formatPrice(quotes[selectedCrypto].low_24h)}
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
                <Activity className="h-4 w-4" />
                24h Volume
              </div>
              <p className="text-lg font-semibold">
                {formatVolume(quotes[selectedCrypto].volume_24h)}
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
                <Clock className="h-4 w-4" />
                Last Update
              </div>
              <p className="text-lg font-semibold">
                {new Date().toLocaleTimeString()}
              </p>
            </div>
          </div>

          {/* Price Range Bar */}
          <div className="mt-6">
            <p className="text-sm text-slate-400 mb-2">24h Price Range</p>
            <div className="relative h-2 bg-slate-700 rounded-full overflow-hidden">
              {(() => {
                const quote = quotes[selectedCrypto]
                const range = quote.high_24h - quote.low_24h
                const position = range > 0 ? ((quote.price - quote.low_24h) / range) * 100 : 50
                return (
                  <>
                    <div
                      className="absolute h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500"
                      style={{ width: '100%' }}
                    />
                    <div
                      className="absolute w-3 h-3 bg-white rounded-full -top-0.5 transform -translate-x-1/2 shadow-lg"
                      style={{ left: `${Math.min(Math.max(position, 2), 98)}%` }}
                    />
                  </>
                )
              })()}
            </div>
            <div className="flex justify-between mt-1 text-xs text-slate-500">
              <span>${formatPrice(quotes[selectedCrypto].low_24h)}</span>
              <span>${formatPrice(quotes[selectedCrypto].high_24h)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Info Section */}
      <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-lg p-6 border border-blue-700/30">
        <h2 className="text-lg font-semibold mb-3">Crypto Trading with ChartSense</h2>
        <div className="grid md:grid-cols-3 gap-4 text-sm text-slate-300">
          <div>
            <p className="font-medium text-white mb-1">24/7 Markets</p>
            <p>Cryptocurrency markets never close. Trade anytime, day or night.</p>
          </div>
          <div>
            <p className="font-medium text-white mb-1">Powered by Alpaca</p>
            <p>Execute trades through Alpaca's crypto trading infrastructure.</p>
          </div>
          <div>
            <p className="font-medium text-white mb-1">Paper Trading</p>
            <p>Practice with paper trading before risking real capital.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
