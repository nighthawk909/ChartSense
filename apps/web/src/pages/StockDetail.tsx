import { useParams } from 'react-router-dom'
import { Star, TrendingUp, TrendingDown, Info } from 'lucide-react'
import StockChart from '../components/StockChart'

// Mock data
const stockData = {
  AAPL: {
    name: 'Apple Inc.',
    price: 178.72,
    change: 2.34,
    changePercent: 1.32,
    open: 176.38,
    high: 179.43,
    low: 175.82,
    volume: 52340000,
    avgVolume: 48920000,
    marketCap: 2780000000000,
    pe: 28.45,
    eps: 6.28,
    dividend: 0.96,
    dividendYield: 0.54,
    week52High: 198.23,
    week52Low: 124.17,
  },
}

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>()
  const stock = stockData[symbol as keyof typeof stockData] || stockData.AAPL

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{symbol}</h1>
            <button className="p-2 hover:bg-slate-700 rounded-lg transition-colors">
              <Star className="h-5 w-5 text-yellow-500" />
            </button>
          </div>
          <p className="text-slate-400">{stock.name}</p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold">${stock.price.toFixed(2)}</p>
          <div
            className={`flex items-center justify-end gap-1 ${
              stock.change >= 0 ? 'text-green-500' : 'text-red-500'
            }`}
          >
            {stock.change >= 0 ? (
              <TrendingUp className="h-5 w-5" />
            ) : (
              <TrendingDown className="h-5 w-5" />
            )}
            <span className="text-lg font-medium">
              {stock.change >= 0 ? '+' : ''}${stock.change.toFixed(2)} (
              {stock.changePercent.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Chart */}
        <div className="col-span-2 space-y-6">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="flex items-center justify-between mb-4">
              <div className="flex gap-2">
                {['1D', '1W', '1M', '3M', '1Y', 'ALL'].map((period) => (
                  <button
                    key={period}
                    className="px-3 py-1 text-sm rounded bg-slate-700 hover:bg-slate-600 transition-colors"
                  >
                    {period}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <button className="px-3 py-1 text-sm rounded bg-blue-600 hover:bg-blue-500 transition-colors">
                  Candlestick
                </button>
                <button className="px-3 py-1 text-sm rounded bg-slate-700 hover:bg-slate-600 transition-colors">
                  Line
                </button>
              </div>
            </div>
            <div className="h-96">
              <StockChart symbol={symbol || 'AAPL'} />
            </div>
          </div>

          {/* Technical Analysis */}
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Technical Analysis</h2>
            <div className="grid grid-cols-2 gap-4">
              <IndicatorSection title="Momentum Indicators">
                <IndicatorRow label="RSI (14)" value="58.42" signal="Neutral" />
                <IndicatorRow label="Stochastic %K" value="72.15" signal="Overbought" />
                <IndicatorRow label="Williams %R" value="-28.5" signal="Neutral" />
                <IndicatorRow label="MACD" value="2.34" signal="Bullish" />
              </IndicatorSection>
              <IndicatorSection title="Moving Averages">
                <IndicatorRow label="SMA (20)" value="175.23" signal="Above" />
                <IndicatorRow label="SMA (50)" value="172.45" signal="Above" />
                <IndicatorRow label="SMA (200)" value="165.89" signal="Above" />
                <IndicatorRow label="EMA (20)" value="176.12" signal="Above" />
              </IndicatorSection>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Key Stats */}
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Key Statistics</h2>
            <div className="space-y-3">
              <StatRow label="Open" value={`$${stock.open.toFixed(2)}`} />
              <StatRow label="High" value={`$${stock.high.toFixed(2)}`} />
              <StatRow label="Low" value={`$${stock.low.toFixed(2)}`} />
              <StatRow
                label="Volume"
                value={formatNumber(stock.volume)}
              />
              <StatRow
                label="Avg Volume"
                value={formatNumber(stock.avgVolume)}
              />
              <StatRow
                label="Market Cap"
                value={formatLargeNumber(stock.marketCap)}
              />
              <StatRow label="52W High" value={`$${stock.week52High.toFixed(2)}`} />
              <StatRow label="52W Low" value={`$${stock.week52Low.toFixed(2)}`} />
            </div>
          </div>

          {/* Fundamentals */}
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Fundamentals</h2>
            <div className="space-y-3">
              <StatRow label="P/E Ratio" value={stock.pe.toFixed(2)} />
              <StatRow label="EPS" value={`$${stock.eps.toFixed(2)}`} />
              <StatRow label="Dividend" value={`$${stock.dividend.toFixed(2)}`} />
              <StatRow
                label="Dividend Yield"
                value={`${stock.dividendYield.toFixed(2)}%`}
              />
            </div>
          </div>

          {/* AI Insight */}
          <div className="bg-gradient-to-br from-blue-900/50 to-purple-900/50 rounded-lg p-4 border border-blue-700/50">
            <div className="flex items-center gap-2 mb-3">
              <Info className="h-5 w-5 text-blue-400" />
              <h2 className="text-lg font-semibold">AI Insight</h2>
            </div>
            <p className="text-sm text-slate-300">
              Based on technical indicators, {symbol} shows a neutral to bullish
              trend. RSI is in neutral territory, and the price is trading above
              key moving averages. Consider watching for a breakout above
              $180.00 for potential upside momentum.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function IndicatorSection({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div>
      <h3 className="text-sm font-medium text-slate-400 mb-3">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function IndicatorRow({
  label,
  value,
  signal,
}: {
  label: string
  value: string
  signal: string
}) {
  const signalColor =
    signal === 'Bullish' || signal === 'Above'
      ? 'text-green-500'
      : signal === 'Bearish' || signal === 'Below' || signal === 'Overbought'
      ? 'text-red-500'
      : 'text-yellow-500'

  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
      <span className="text-sm text-slate-400">{label}</span>
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium">{value}</span>
        <span className={`text-xs ${signalColor}`}>{signal}</span>
      </div>
    </div>
  )
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-slate-400">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  )
}

function formatNumber(num: number): string {
  return num.toLocaleString()
}

function formatLargeNumber(num: number): string {
  if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`
  if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`
  if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`
  return `$${num.toLocaleString()}`
}
