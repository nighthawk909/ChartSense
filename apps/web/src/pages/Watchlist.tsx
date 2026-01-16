import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Trash2, TrendingUp, TrendingDown, Search } from 'lucide-react'

interface WatchlistStock {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  volume: number
  marketCap: number
}

const mockWatchlist: WatchlistStock[] = [
  { symbol: 'AAPL', name: 'Apple Inc.', price: 178.72, change: 2.34, changePercent: 1.32, volume: 52340000, marketCap: 2780000000000 },
  { symbol: 'MSFT', name: 'Microsoft Corp.', price: 378.91, change: -1.23, changePercent: -0.32, volume: 21450000, marketCap: 2810000000000 },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 141.80, change: 3.45, changePercent: 2.49, volume: 18920000, marketCap: 1780000000000 },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 178.25, change: -2.15, changePercent: -1.19, volume: 32100000, marketCap: 1850000000000 },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', price: 875.28, change: 15.67, changePercent: 1.82, volume: 45230000, marketCap: 2150000000000 },
  { symbol: 'META', name: 'Meta Platforms', price: 505.45, change: 8.23, changePercent: 1.65, volume: 15670000, marketCap: 1290000000000 },
  { symbol: 'TSLA', name: 'Tesla Inc.', price: 248.50, change: -5.45, changePercent: -2.14, volume: 98450000, marketCap: 789000000000 },
]

export default function Watchlist() {
  const [watchlist, setWatchlist] = useState(mockWatchlist)
  const [searchQuery, setSearchQuery] = useState('')
  // TODO: Implement add modal
  const [, setShowAddModal] = useState(false)

  const filteredWatchlist = watchlist.filter(
    (stock) =>
      stock.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      stock.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const removeFromWatchlist = (symbol: string) => {
    setWatchlist(watchlist.filter((s) => s.symbol !== symbol))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Watchlist</h1>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Stock
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
        <input
          type="text"
          placeholder="Search watchlist..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Table */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-400">
                Symbol
              </th>
              <th className="text-left px-6 py-4 text-sm font-medium text-slate-400">
                Name
              </th>
              <th className="text-right px-6 py-4 text-sm font-medium text-slate-400">
                Price
              </th>
              <th className="text-right px-6 py-4 text-sm font-medium text-slate-400">
                Change
              </th>
              <th className="text-right px-6 py-4 text-sm font-medium text-slate-400">
                Volume
              </th>
              <th className="text-right px-6 py-4 text-sm font-medium text-slate-400">
                Market Cap
              </th>
              <th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody>
            {filteredWatchlist.map((stock) => (
              <tr
                key={stock.symbol}
                className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors"
              >
                <td className="px-6 py-4">
                  <Link
                    to={`/stock/${stock.symbol}`}
                    className="font-medium text-blue-400 hover:text-blue-300"
                  >
                    {stock.symbol}
                  </Link>
                </td>
                <td className="px-6 py-4 text-slate-300">{stock.name}</td>
                <td className="px-6 py-4 text-right font-medium">
                  ${stock.price.toFixed(2)}
                </td>
                <td className="px-6 py-4 text-right">
                  <div
                    className={`flex items-center justify-end gap-1 ${
                      stock.change >= 0 ? 'text-green-500' : 'text-red-500'
                    }`}
                  >
                    {stock.change >= 0 ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : (
                      <TrendingDown className="h-4 w-4" />
                    )}
                    <span>
                      {stock.change >= 0 ? '+' : ''}
                      {stock.changePercent.toFixed(2)}%
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 text-right text-slate-300">
                  {formatNumber(stock.volume)}
                </td>
                <td className="px-6 py-4 text-right text-slate-300">
                  {formatLargeNumber(stock.marketCap)}
                </td>
                <td className="px-6 py-4">
                  <button
                    onClick={() => removeFromWatchlist(stock.symbol)}
                    className="p-2 text-slate-400 hover:text-red-500 hover:bg-slate-700 rounded-lg transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredWatchlist.length === 0 && (
          <div className="text-center py-12 text-slate-400">
            {searchQuery
              ? 'No stocks match your search'
              : 'Your watchlist is empty. Add some stocks to get started!'}
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Total Stocks"
          value={watchlist.length.toString()}
        />
        <StatCard
          label="Gainers"
          value={watchlist.filter((s) => s.change > 0).length.toString()}
          valueColor="text-green-500"
        />
        <StatCard
          label="Losers"
          value={watchlist.filter((s) => s.change < 0).length.toString()}
          valueColor="text-red-500"
        />
        <StatCard
          label="Unchanged"
          value={watchlist.filter((s) => s.change === 0).length.toString()}
          valueColor="text-slate-400"
        />
      </div>
    </div>
  )
}

function StatCard({
  label,
  value,
  valueColor = 'text-white',
}: {
  label: string
  value: string
  valueColor?: string
}) {
  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <p className="text-sm text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${valueColor}`}>{value}</p>
    </div>
  )
}

function formatNumber(num: number): string {
  if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`
  if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`
  return num.toLocaleString()
}

function formatLargeNumber(num: number): string {
  if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`
  if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`
  if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`
  return `$${num.toLocaleString()}`
}
