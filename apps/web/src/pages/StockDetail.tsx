import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Star, TrendingUp, TrendingDown, Info, Loader2, RefreshCw, Activity, Target, GitBranch } from 'lucide-react'
import StockChart from '../components/StockChart'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface StockQuote {
  symbol: string
  price: number
  change: number
  change_percent: number
  volume: number
  latest_trading_day: string
  previous_close: number
  open: number
  high: number
  low: number
}

interface TechnicalAnalysis {
  rsi?: { value: number; signal: string }
  macd?: { macd_line: number; signal_line: number; histogram: number; signal: string }
  sma_20?: number
}

interface SupportResistance {
  current_price: number
  support_levels: Array<{ price: number; strength: number; touches: number; distance_pct: number }>
  resistance_levels: Array<{ price: number; strength: number; touches: number; distance_pct: number }>
  nearest_support: number | null
  nearest_resistance: number | null
}

interface ElliottWave {
  wave_count: number
  wave_type: string
  direction: string
  current_position: string
  confidence: number
  next_target: number | null
  description: string
}

interface TrendLine {
  type: string
  direction: string
  strength: number
  touches: number
  current_value: number
}

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>()
  const [quote, setQuote] = useState<StockQuote | null>(null)
  const [technicals, setTechnicals] = useState<TechnicalAnalysis>({})
  const [supportResistance, setSupportResistance] = useState<SupportResistance | null>(null)
  const [elliottWave, setElliottWave] = useState<ElliottWave | null>(null)
  const [trendLines, setTrendLines] = useState<TrendLine[]>([])
  const [loading, setLoading] = useState(true)
  const [chartType, setChartType] = useState<'candlestick' | 'line'>('candlestick')
  const [period, setPeriod] = useState('1M')
  const [watchlisted, setWatchlisted] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const fetchQuote = async () => {
    if (!symbol) return
    try {
      const response = await fetch(`${API_URL}/api/stocks/quote/${symbol}`)
      if (response.ok) {
        const data = await response.json()
        setQuote(data)
      }
    } catch (error) {
      console.error('Failed to fetch quote:', error)
    }
  }

  const fetchTechnicals = async () => {
    if (!symbol) return
    try {
      const [rsiRes, macdRes, smaRes] = await Promise.all([
        fetch(`${API_URL}/api/analysis/rsi/${symbol}`),
        fetch(`${API_URL}/api/analysis/macd/${symbol}`),
        fetch(`${API_URL}/api/analysis/sma/${symbol}?period=20`),
      ])

      const newTechnicals: TechnicalAnalysis = {}

      if (rsiRes.ok) {
        const rsiData = await rsiRes.json()
        newTechnicals.rsi = rsiData
      }
      if (macdRes.ok) {
        const macdData = await macdRes.json()
        newTechnicals.macd = macdData
      }
      if (smaRes.ok) {
        const smaData = await smaRes.json()
        newTechnicals.sma_20 = smaData.value
      }

      setTechnicals(newTechnicals)
    } catch (error) {
      console.error('Failed to fetch technicals:', error)
    }
  }

  const fetchAdvancedAnalysis = async () => {
    if (!symbol) return
    try {
      const [srRes, ewRes, tlRes] = await Promise.all([
        fetch(`${API_URL}/api/advanced/support-resistance/${symbol}`),
        fetch(`${API_URL}/api/advanced/elliott-wave/${symbol}`),
        fetch(`${API_URL}/api/advanced/trend-lines/${symbol}`),
      ])

      if (srRes.ok) {
        const srData = await srRes.json()
        setSupportResistance(srData)
      }
      if (ewRes.ok) {
        const ewData = await ewRes.json()
        setElliottWave(ewData.elliott_wave)
      }
      if (tlRes.ok) {
        const tlData = await tlRes.json()
        setTrendLines(tlData.trend_lines || [])
      }
    } catch (error) {
      console.error('Failed to fetch advanced analysis:', error)
    }
  }

  const toggleWatchlist = async () => {
    if (!symbol) return
    try {
      if (watchlisted) {
        await fetch(`${API_URL}/api/watchlist/remove/${symbol}`, { method: 'DELETE' })
      } else {
        await fetch(`${API_URL}/api/watchlist/add`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol }),
        })
      }
      setWatchlisted(!watchlisted)
    } catch (error) {
      console.error('Failed to toggle watchlist:', error)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await Promise.all([fetchQuote(), fetchTechnicals(), fetchAdvancedAnalysis()])
    setRefreshing(false)
  }

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchQuote(), fetchTechnicals(), fetchAdvancedAnalysis()])
      .finally(() => setLoading(false))

    const interval = setInterval(fetchQuote, 30000)
    return () => clearInterval(interval)
  }, [symbol])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    )
  }

  const getRsiSignal = (value: number) => {
    if (value > 70) return { text: 'Overbought', color: 'text-red-500' }
    if (value < 30) return { text: 'Oversold', color: 'text-green-500' }
    return { text: 'Neutral', color: 'text-yellow-500' }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{symbol}</h1>
            <button
              onClick={toggleWatchlist}
              className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <Star className={`h-5 w-5 ${watchlisted ? 'text-yellow-500 fill-yellow-500' : 'text-slate-400'}`} />
            </button>
            <button
              onClick={handleRefresh}
              className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
              disabled={refreshing}
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <p className="text-slate-400">
            Last updated: {quote?.latest_trading_day || 'N/A'}
          </p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold">${quote?.price?.toFixed(2) || '—'}</p>
          {quote && (
            <div className={`flex items-center justify-end gap-1 ${quote.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {quote.change >= 0 ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
              <span className="text-lg font-medium">
                {quote.change >= 0 ? '+' : ''}{quote.change?.toFixed(2)} ({quote.change_percent?.toFixed(2)}%)
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Chart */}
        <div className="col-span-2 space-y-6">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="flex items-center justify-between mb-4">
              <div className="flex gap-2">
                {['1D', '1W', '1M', '3M', '1Y', 'ALL'].map((p) => (
                  <button
                    key={p}
                    onClick={() => setPeriod(p)}
                    className={`px-3 py-1 text-sm rounded transition-colors ${
                      period === p ? 'bg-blue-600 text-white' : 'bg-slate-700 hover:bg-slate-600'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setChartType('candlestick')}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    chartType === 'candlestick' ? 'bg-blue-600 text-white' : 'bg-slate-700 hover:bg-slate-600'
                  }`}
                >
                  Candlestick
                </button>
                <button
                  onClick={() => setChartType('line')}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    chartType === 'line' ? 'bg-blue-600 text-white' : 'bg-slate-700 hover:bg-slate-600'
                  }`}
                >
                  Line
                </button>
              </div>
            </div>
            <div className="h-96">
              <StockChart symbol={symbol || 'AAPL'} chartType={chartType} period={period} />
            </div>
          </div>

          {/* Technical Analysis */}
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Technical Analysis</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-3">Momentum Indicators</h3>
                <div className="space-y-2">
                  {technicals.rsi && (
                    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
                      <span className="text-sm text-slate-400">RSI (14)</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium">{technicals.rsi.value?.toFixed(2)}</span>
                        <span className={`text-xs ${getRsiSignal(technicals.rsi.value).color}`}>
                          {getRsiSignal(technicals.rsi.value).text}
                        </span>
                      </div>
                    </div>
                  )}
                  {technicals.macd && (
                    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
                      <span className="text-sm text-slate-400">MACD</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium">{technicals.macd.macd_line?.toFixed(2)}</span>
                        <span className={`text-xs ${technicals.macd.histogram > 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {technicals.macd.histogram > 0 ? 'Bullish' : 'Bearish'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-3">Moving Averages</h3>
                <div className="space-y-2">
                  {technicals.sma_20 && (
                    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
                      <span className="text-sm text-slate-400">SMA (20)</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium">${technicals.sma_20?.toFixed(2)}</span>
                        <span className={`text-xs ${quote && quote.price > technicals.sma_20 ? 'text-green-500' : 'text-red-500'}`}>
                          {quote && quote.price > technicals.sma_20 ? 'Above' : 'Below'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Key Statistics</h2>
            <div className="space-y-3">
              <StatRow label="Open" value={quote?.open ? `$${quote.open.toFixed(2)}` : '—'} />
              <StatRow label="High" value={quote?.high ? `$${quote.high.toFixed(2)}` : '—'} />
              <StatRow label="Low" value={quote?.low ? `$${quote.low.toFixed(2)}` : '—'} />
              <StatRow label="Prev Close" value={quote?.previous_close ? `$${quote.previous_close.toFixed(2)}` : '—'} />
              <StatRow label="Volume" value={quote?.volume ? quote.volume.toLocaleString() : '—'} />
            </div>
          </div>

          <div className="bg-gradient-to-br from-blue-900/50 to-purple-900/50 rounded-lg p-4 border border-blue-700/50">
            <div className="flex items-center gap-2 mb-3">
              <Info className="h-5 w-5 text-blue-400" />
              <h2 className="text-lg font-semibold">AI Insight</h2>
            </div>
            <p className="text-sm text-slate-300">
              {technicals.rsi && technicals.rsi.value > 70
                ? `${symbol} is overbought (RSI: ${technicals.rsi.value.toFixed(1)}). Consider taking profits.`
                : technicals.rsi && technicals.rsi.value < 30
                ? `${symbol} is oversold (RSI: ${technicals.rsi.value.toFixed(1)}). Potential buying opportunity.`
                : `${symbol} is in neutral territory. Watch for breakouts.`}
            </p>
          </div>

          {/* Support & Resistance */}
          {supportResistance && (
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="flex items-center gap-2 mb-3">
                <Target className="h-5 w-5 text-yellow-500" />
                <h2 className="text-lg font-semibold">Support & Resistance</h2>
              </div>
              <div className="space-y-3">
                {supportResistance.nearest_resistance && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-red-400">Resistance</span>
                    <span className="text-sm font-medium">${supportResistance.nearest_resistance.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex items-center justify-between bg-slate-700/50 px-2 py-1 rounded">
                  <span className="text-sm text-slate-400">Current</span>
                  <span className="text-sm font-medium">${supportResistance.current_price.toFixed(2)}</span>
                </div>
                {supportResistance.nearest_support && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-green-400">Support</span>
                    <span className="text-sm font-medium">${supportResistance.nearest_support.toFixed(2)}</span>
                  </div>
                )}
                {supportResistance.support_levels.length > 1 && (
                  <div className="pt-2 border-t border-slate-700">
                    <p className="text-xs text-slate-500 mb-1">Other Levels</p>
                    <div className="flex flex-wrap gap-1">
                      {supportResistance.support_levels.slice(0, 3).map((level, i) => (
                        <span key={i} className="text-xs bg-green-900/50 text-green-400 px-2 py-0.5 rounded">
                          ${level.price}
                        </span>
                      ))}
                      {supportResistance.resistance_levels.slice(0, 3).map((level, i) => (
                        <span key={i} className="text-xs bg-red-900/50 text-red-400 px-2 py-0.5 rounded">
                          ${level.price}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Elliott Wave */}
          {elliottWave && (
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="h-5 w-5 text-purple-500" />
                <h2 className="text-lg font-semibold">Elliott Wave</h2>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Wave Type</span>
                  <span className={`text-sm font-medium capitalize ${elliottWave.direction === 'bullish' ? 'text-green-500' : 'text-red-500'}`}>
                    {elliottWave.wave_type} ({elliottWave.direction})
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Position</span>
                  <span className="text-sm font-medium">{elliottWave.current_position}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Confidence</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${elliottWave.confidence >= 70 ? 'bg-green-500' : elliottWave.confidence >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                        style={{ width: `${elliottWave.confidence}%` }}
                      />
                    </div>
                    <span className="text-xs">{elliottWave.confidence}%</span>
                  </div>
                </div>
                {elliottWave.next_target && (
                  <div className="flex items-center justify-between pt-2 border-t border-slate-700">
                    <span className="text-sm text-slate-400">Target</span>
                    <span className="text-sm font-medium text-blue-400">${elliottWave.next_target}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Trend Lines */}
          {trendLines.length > 0 && (
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="flex items-center gap-2 mb-3">
                <GitBranch className="h-5 w-5 text-cyan-500" />
                <h2 className="text-lg font-semibold">Trend Lines</h2>
              </div>
              <div className="space-y-2">
                {trendLines.map((line, i) => (
                  <div key={i} className="flex items-center justify-between py-1 border-b border-slate-700/50 last:border-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded capitalize ${
                        line.type === 'support' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
                      }`}>
                        {line.type}
                      </span>
                      <span className="text-xs text-slate-500 capitalize">{line.direction}</span>
                    </div>
                    <span className="text-sm font-medium">${line.current_value.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
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
