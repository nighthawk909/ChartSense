import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, Star } from 'lucide-react'
import StockChart from '../components/StockChart'

// Mock data for demonstration
const mockWatchlist = [
  { symbol: 'AAPL', name: 'Apple Inc.', price: 178.72, change: 2.34, changePercent: 1.32 },
  { symbol: 'MSFT', name: 'Microsoft Corp.', price: 378.91, change: -1.23, changePercent: -0.32 },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 141.80, change: 3.45, changePercent: 2.49 },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 178.25, change: -2.15, changePercent: -1.19 },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', price: 875.28, change: 15.67, changePercent: 1.82 },
]

const marketIndices = [
  { symbol: 'SPY', name: 'S&P 500', price: 4783.45, change: 12.34, changePercent: 0.26 },
  { symbol: 'QQQ', name: 'Nasdaq 100', price: 16234.56, change: 45.67, changePercent: 0.28 },
  { symbol: 'DIA', name: 'Dow Jones', price: 37689.12, change: -23.45, changePercent: -0.06 },
]

type TimeInterval = '1min' | '5min' | '15min' | '30min' | '60min' | 'daily'

export default function Dashboard() {
  const [selectedStock, setSelectedStock] = useState('AAPL')
  const [selectedPeriod, setSelectedPeriod] = useState('1M')
  const [selectedInterval, setSelectedInterval] = useState<TimeInterval>('daily')

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
      {/* Market Overview */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Market Overview</h2>
        <div className="grid grid-cols-3 gap-4">
          {marketIndices.map((index) => (
            <div
              key={index.symbol}
              className="bg-slate-800 rounded-lg p-4 border border-slate-700"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">{index.name}</p>
                  <p className="text-xl font-semibold">{index.price.toLocaleString()}</p>
                </div>
                <div
                  className={`flex items-center gap-1 ${
                    index.change >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}
                >
                  {index.change >= 0 ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : (
                    <TrendingDown className="h-4 w-4" />
                  )}
                  <span className="font-medium">
                    {index.change >= 0 ? '+' : ''}
                    {index.changePercent.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-3 gap-6">
        {/* Chart */}
        <div className="col-span-2">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">{selectedStock} Chart</h2>
              <div className="flex gap-4">
                {/* Interval selector */}
                <div className="flex gap-1 bg-slate-900 rounded-lg p-1">
                  {intervals.map((int) => (
                    <button
                      key={int.value}
                      onClick={() => setSelectedInterval(int.value)}
                      className={`px-2 py-1 text-xs rounded transition-colors ${
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
                <div className="flex gap-1">
                  {periods.map((period) => (
                    <button
                      key={period}
                      onClick={() => setSelectedPeriod(period)}
                      className={`px-3 py-1 text-sm rounded transition-colors ${
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
              {mockWatchlist.map((stock) => (
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
                    <p className="font-medium">${stock.price.toFixed(2)}</p>
                    <p
                      className={`text-sm ${
                        stock.change >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}
                    >
                      {stock.change >= 0 ? '+' : ''}
                      {stock.changePercent.toFixed(2)}%
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Technical Indicators */}
      <section>
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <h2 className="text-lg font-semibold mb-4">Technical Indicators - {selectedStock}</h2>
          <div className="grid grid-cols-4 gap-4">
            <IndicatorCard
              name="RSI (14)"
              value={58.42}
              status="Neutral"
              statusColor="text-yellow-500"
            />
            <IndicatorCard
              name="MACD"
              value={2.34}
              status="Bullish"
              statusColor="text-green-500"
            />
            <IndicatorCard
              name="SMA (50)"
              value={172.45}
              status="Above"
              statusColor="text-green-500"
            />
            <IndicatorCard
              name="Bollinger Bands"
              value="Middle"
              status="Neutral"
              statusColor="text-yellow-500"
            />
          </div>
        </div>
      </section>
    </div>
  )
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
