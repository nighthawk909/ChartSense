import { TrendingUp, TrendingDown } from 'lucide-react'
import { StockQuote, marketIndices } from '../../hooks/useDashboardData'

interface MarketOverviewProps {
  indices: Record<string, StockQuote>
}

export default function MarketOverview({ indices }: MarketOverviewProps) {
  return (
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
  )
}
