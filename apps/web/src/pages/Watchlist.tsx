import { useState, useEffect } from 'react'
import { Plus, BarChart3, Eye, X, Search, TrendingUp, Bitcoin, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import HybridWatchlist from '../components/watchlist/HybridWatchlist'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface SearchResult {
  symbol: string
  name: string
  type: string
  exchange?: string
}

export default function Watchlist() {
  const navigate = useNavigate()
  const [assetClass, setAssetClass] = useState<'stocks' | 'crypto' | 'both'>('both')
  const [showAddModal, setShowAddModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [adding, setAdding] = useState<string | null>(null)
  const [addedSymbols, setAddedSymbols] = useState<Set<string>>(new Set())

  // Popular symbols for quick add
  const popularStocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
  const popularCrypto = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'XRP/USD']

  // Search for symbols
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 1) {
      setSearchResults([])
      return
    }

    const searchTimer = setTimeout(async () => {
      setSearching(true)
      try {
        const response = await fetch(`${API_URL}/api/stocks/search?query=${encodeURIComponent(searchQuery)}`)
        if (response.ok) {
          const data = await response.json()
          setSearchResults(data.results || [])
        }
      } catch (err) {
        console.error('Search failed:', err)
      } finally {
        setSearching(false)
      }
    }, 300)

    return () => clearTimeout(searchTimer)
  }, [searchQuery])

  const handleSymbolSelect = (symbol: string) => {
    // All symbols now go to the unified stock detail page
    // Encode the symbol for URL (handles / in crypto symbols like BTC/USD)
    const encodedSymbol = encodeURIComponent(symbol)
    navigate(`/stock/${encodedSymbol}`)
  }

  const handleAddSymbol = async (symbol: string) => {
    setAdding(symbol)
    try {
      // Determine if crypto or stock
      const isCrypto = symbol.includes('/') || symbol.endsWith('USD') || symbol.endsWith('USDT')

      const response = await fetch(`${API_URL}/api/watchlist/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          asset_class: isCrypto ? 'crypto' : 'stock'
        })
      })

      if (response.ok) {
        setAddedSymbols(prev => new Set([...prev, symbol]))
        // Keep modal open so user can add more
      } else {
        console.error('Failed to add symbol')
      }
    } catch (err) {
      console.error('Add symbol error:', err)
    } finally {
      setAdding(null)
    }
  }

  const closeModal = () => {
    setShowAddModal(false)
    setSearchQuery('')
    setSearchResults([])
    // If symbols were added, force a refresh of the watchlist
    if (addedSymbols.size > 0) {
      setAddedSymbols(new Set())
      // The HybridWatchlist will refresh on its own interval
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Eye className="w-6 h-6 text-blue-400" />
            Watchlist
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Track stocks and crypto with AI-powered insights
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Asset Class Toggle */}
          <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
            <button
              onClick={() => setAssetClass('both')}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                assetClass === 'both'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setAssetClass('stocks')}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                assetClass === 'stocks'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Stocks
            </button>
            <button
              onClick={() => setAssetClass('crypto')}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                assetClass === 'crypto'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Crypto
            </button>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors"
          >
            <Plus className="h-4 w-4" />
            Add Symbol
          </button>
        </div>
      </div>

      {/* Main Watchlist Component */}
      <HybridWatchlist
        assetClass={assetClass}
        onSymbolSelect={handleSymbolSelect}
        showCarousel={true}
      />

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        <QuickStatCard
          label="Watching"
          icon={<Eye className="w-4 h-4" />}
          description="Symbols in watchlist"
        />
        <QuickStatCard
          label="Active Positions"
          icon={<BarChart3 className="w-4 h-4" />}
          description="Currently trading"
          highlight
        />
        <QuickStatCard
          label="Bot Discoveries"
          icon={<span className="text-purple-400">✨</span>}
          description="AI-found opportunities"
        />
        <QuickStatCard
          label="Signals Today"
          icon={<span className="text-green-400">📊</span>}
          description="Generated signals"
        />
      </div>

      {/* Help Text */}
      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
        <h3 className="text-sm font-medium text-slate-300 mb-2">How the Watchlist Works</h3>
        <ul className="text-xs text-slate-400 space-y-1">
          <li>• <strong>Active Positions</strong>: Symbols you currently hold (green indicator)</li>
          <li>• <strong>Watching</strong>: Symbols you're monitoring for opportunities</li>
          <li>• <strong>Discovered</strong>: Symbols the bot found with high confidence signals (purple sparkle)</li>
          <li>• <strong>AI Insights Carousel</strong>: Swipe through AI analysis for each symbol</li>
          <li>• Click any row to view detailed chart and analysis</li>
        </ul>
      </div>

      {/* Add Symbol Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl w-full max-w-lg border border-slate-700 shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-700">
              <h2 className="text-lg font-semibold text-white">Add Symbol to Watchlist</h2>
              <button
                onClick={closeModal}
                className="p-1 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Search Input */}
            <div className="p-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search stocks or crypto (e.g., AAPL, BTC)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && searchQuery.trim()) {
                      e.preventDefault()
                      handleAddSymbol(searchQuery.trim().toUpperCase())
                    }
                  }}
                  className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoFocus
                />
                {searching && (
                  <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-blue-400 animate-spin" />
                )}
              </div>
              <p className="text-xs text-slate-500 mt-1">Press Enter to add symbol directly</p>

              {/* Search Results */}
              {searchResults.length > 0 && (
                <div className="mt-3 max-h-48 overflow-y-auto space-y-1">
                  {searchResults.map((result) => (
                    <button
                      key={result.symbol}
                      onClick={() => handleAddSymbol(result.symbol)}
                      disabled={adding === result.symbol || addedSymbols.has(result.symbol)}
                      className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                        addedSymbols.has(result.symbol)
                          ? 'bg-green-500/20 border border-green-500/30'
                          : 'bg-slate-700/50 hover:bg-slate-700'
                      }`}
                    >
                      <div className="text-left">
                        <p className="font-medium text-white">{result.symbol}</p>
                        <p className="text-sm text-slate-400">{result.name}</p>
                      </div>
                      {adding === result.symbol ? (
                        <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                      ) : addedSymbols.has(result.symbol) ? (
                        <span className="text-green-400 text-sm">Added ✓</span>
                      ) : (
                        <Plus className="w-5 h-5 text-slate-400" />
                      )}
                    </button>
                  ))}
                </div>
              )}

              {/* No search results - offer direct add */}
              {searchQuery && searchResults.length === 0 && !searching && (
                <div className="mt-3 p-4 bg-slate-700/30 rounded-lg border border-slate-600">
                  <p className="text-sm text-slate-400 mb-3">
                    No results found for "{searchQuery.toUpperCase()}"
                  </p>
                  <button
                    onClick={() => handleAddSymbol(searchQuery.toUpperCase())}
                    disabled={adding === searchQuery.toUpperCase() || addedSymbols.has(searchQuery.toUpperCase())}
                    className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                      addedSymbols.has(searchQuery.toUpperCase())
                        ? 'bg-green-500/20 border border-green-500/30'
                        : 'bg-blue-600 hover:bg-blue-500'
                    }`}
                  >
                    <div className="text-left">
                      <p className="font-medium text-white">Add "{searchQuery.toUpperCase()}" anyway</p>
                      <p className="text-xs text-slate-300">Symbol will be validated when fetching price</p>
                    </div>
                    {adding === searchQuery.toUpperCase() ? (
                      <Loader2 className="w-5 h-5 text-white animate-spin" />
                    ) : addedSymbols.has(searchQuery.toUpperCase()) ? (
                      <span className="text-green-400 text-sm">Added ✓</span>
                    ) : (
                      <Plus className="w-5 h-5 text-white" />
                    )}
                  </button>
                </div>
              )}

              {/* Quick Add Sections */}
              {!searchQuery && (
                <div className="mt-4 space-y-4">
                  {/* Popular Stocks */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="w-4 h-4 text-green-400" />
                      <span className="text-sm font-medium text-slate-300">Popular Stocks</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {popularStocks.map((symbol) => (
                        <button
                          key={symbol}
                          onClick={() => handleAddSymbol(symbol)}
                          disabled={adding === symbol || addedSymbols.has(symbol)}
                          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            addedSymbols.has(symbol)
                              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                              : 'bg-slate-700 text-white hover:bg-slate-600'
                          }`}
                        >
                          {adding === symbol ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : addedSymbols.has(symbol) ? (
                            `${symbol} ✓`
                          ) : (
                            symbol
                          )}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Popular Crypto */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Bitcoin className="w-4 h-4 text-orange-400" />
                      <span className="text-sm font-medium text-slate-300">Popular Crypto</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {popularCrypto.map((symbol) => (
                        <button
                          key={symbol}
                          onClick={() => handleAddSymbol(symbol)}
                          disabled={adding === symbol || addedSymbols.has(symbol)}
                          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            addedSymbols.has(symbol)
                              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                              : 'bg-slate-700 text-white hover:bg-slate-600'
                          }`}
                        >
                          {adding === symbol ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : addedSymbols.has(symbol) ? (
                            `${symbol} ✓`
                          ) : (
                            symbol
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between p-4 border-t border-slate-700 bg-slate-800/50">
              <span className="text-sm text-slate-400">
                {addedSymbols.size > 0 && `${addedSymbols.size} symbol(s) added`}
              </span>
              <button
                onClick={closeModal}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function QuickStatCard({
  label,
  icon,
  description,
  highlight = false,
}: {
  label: string
  icon: React.ReactNode
  description: string
  highlight?: boolean
}) {
  return (
    <div className={`bg-slate-800 rounded-lg p-4 border ${highlight ? 'border-green-500/30' : 'border-slate-700'}`}>
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-sm font-medium text-slate-300">{label}</span>
      </div>
      <p className="text-xs text-slate-500">{description}</p>
    </div>
  )
}
