import { Link } from 'react-router-dom'
import { Briefcase } from 'lucide-react'
import { WatchlistStock, Position } from '../../hooks/useDashboardData'

interface WatchlistPanelProps {
  watchlist: WatchlistStock[]
  positions: Position[]
  selectedStock: string
  setSelectedStock: (stock: string) => void
}

export default function WatchlistPanel({
  watchlist,
  positions,
  selectedStock,
  setSelectedStock,
}: WatchlistPanelProps) {
  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">
            {positions.length > 0 ? 'Positions & Watchlist' : 'Watchlist'}
          </h2>
          {positions.length > 0 && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
              <Briefcase className="w-3 h-3" />
              {positions.length} held
            </span>
          )}
        </div>
        <Link
          to="/bot"
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
                : stock.isPosition
                  ? 'bg-green-500/10 hover:bg-green-500/20 border border-green-500/30'
                  : 'hover:bg-slate-700'
            }`}
          >
            <div className="text-left">
              <div className="flex items-center gap-2">
                <p className="font-medium">{stock.symbol}</p>
                {stock.isPosition && (
                  <span className="px-1.5 py-0.5 bg-green-500/30 text-green-400 text-xs rounded font-medium">
                    HELD
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-400">{stock.name}</p>
            </div>
            <div className="text-right">
              <p className="font-medium">
                {stock.price > 0 ? `$${stock.price.toFixed(2)}` : '--'}
              </p>
              {/* Show unrealized P&L for positions, daily change for others */}
              {stock.isPosition && stock.unrealizedPnlPct !== undefined ? (
                <p
                  className={`text-sm font-medium ${
                    stock.unrealizedPnlPct >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}
                >
                  {stock.unrealizedPnlPct >= 0 ? '+' : ''}
                  {stock.unrealizedPnlPct.toFixed(2)}% P&L
                </p>
              ) : (
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
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
