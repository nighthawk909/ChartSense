import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Star, TrendingUp, TrendingDown, Loader2, RefreshCw, Target, GitBranch } from 'lucide-react'
import StockChart from '../components/StockChart'
import MultiTimeframeInsight from '../components/indicators/MultiTimeframeInsight'
import TripleScreenPanel from '../components/indicators/TripleScreenPanel'
import PatternInsights from '../components/indicators/PatternInsights'

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

interface AIInsight {
  symbol: string
  current_price: number
  daily_change_pct: number
  score: number
  recommendation: string
  recommendation_color: string
  action: string
  insight: string
  signals: string[]
  concerns: string[]
  indicators: {
    rsi_14: number
    macd: number
    macd_signal: number
    macd_histogram: number
    sma_20: number
    sma_50: number
    sma_200: number
    atr_14: number
    volume_ratio: number
  }
  price_vs_ma: {
    above_sma_20: boolean
    above_sma_50: boolean
    above_sma_200: boolean
  }
  momentum: {
    week_change_pct: number
    month_change_pct: number
  }
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
  const [aiInsight, setAiInsight] = useState<AIInsight | null>(null)
  const [_aiInsightLoading, setAiInsightLoading] = useState(false)
  const [supportResistance, setSupportResistance] = useState<SupportResistance | null>(null)
  const [_elliottWave, setElliottWave] = useState<ElliottWave | null>(null)
  const [trendLines, setTrendLines] = useState<TrendLine[]>([])
  const [loading, setLoading] = useState(true)
  const [chartType, setChartType] = useState<'candlestick' | 'line'>('candlestick')
  const [period, setPeriod] = useState('1M')
  const [interval, setInterval] = useState<'1min' | '5min' | '15min' | '30min' | '60min' | 'daily'>('daily')
  const [watchlisted, setWatchlisted] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [lastQuoteUpdate, setLastQuoteUpdate] = useState<Date | null>(null)
  const [secondsAgo, setSecondsAgo] = useState(0)

  const fetchQuote = async () => {
    if (!symbol) return
    try {
      const response = await fetch(`${API_URL}/api/stocks/quote/${symbol}`)
      if (response.ok) {
        const data = await response.json()
        setQuote(data)
        setLastQuoteUpdate(new Date())
        setSecondsAgo(0)
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

  const fetchAiInsight = async () => {
    if (!symbol) return
    setAiInsightLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/analysis/ai-insight/${symbol}`)
      if (response.ok) {
        const data = await response.json()
        setAiInsight(data)
      }
    } catch (error) {
      console.error('Failed to fetch AI insight:', error)
    } finally {
      setAiInsightLoading(false)
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
    await Promise.all([fetchQuote(), fetchTechnicals(), fetchAdvancedAnalysis(), fetchAiInsight()])
    setRefreshing(false)
  }

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchQuote(), fetchTechnicals(), fetchAdvancedAnalysis(), fetchAiInsight()])
      .finally(() => setLoading(false))

    const quoteInterval = window.setInterval(fetchQuote, 30000)

    // Update "seconds ago" counter every second
    const timerInterval = window.setInterval(() => {
      setSecondsAgo(prev => prev + 1)
    }, 1000)

    return () => {
      clearInterval(quoteInterval)
      clearInterval(timerInterval)
    }
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
          <div className="flex items-center gap-3 mt-1">
            <span className="text-slate-500 text-sm">Trading day: {quote?.latest_trading_day || 'N/A'}</span>
            {lastQuoteUpdate && (
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${secondsAgo < 10 ? 'bg-green-500' : secondsAgo < 30 ? 'bg-yellow-500' : 'bg-orange-500'} ${secondsAgo < 30 ? 'animate-pulse' : ''}`}></span>
                <span className={`text-xs ${secondsAgo < 10 ? 'text-green-400' : secondsAgo < 30 ? 'text-yellow-400' : 'text-orange-400'}`}>
                  {secondsAgo < 60 ? `${secondsAgo}s ago` : `${Math.floor(secondsAgo / 60)}m ago`}
                </span>
              </div>
            )}
          </div>
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
            {/* Chart Controls */}
            <div className="flex flex-col gap-3 mb-4">
              {/* Interval selector (granularity) */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 w-16">Interval:</span>
                <div className="flex gap-1">
                  {[
                    { value: '1min', label: '1m' },
                    { value: '5min', label: '5m' },
                    { value: '15min', label: '15m' },
                    { value: '30min', label: '30m' },
                    { value: '60min', label: '1h' },
                    { value: 'daily', label: '1D' },
                  ].map((i) => (
                    <button
                      key={i.value}
                      onClick={() => setInterval(i.value as typeof interval)}
                      className={`px-2 py-1 text-xs rounded transition-colors ${
                        interval === i.value ? 'bg-green-600 text-white' : 'bg-slate-700 hover:bg-slate-600'
                      }`}
                    >
                      {i.label}
                    </button>
                  ))}
                </div>
              </div>
              {/* Period and chart type */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 w-16">Period:</span>
                  <div className="flex gap-1">
                    {['1D', '1W', '1M', '3M', '1Y', 'ALL'].map((p) => (
                      <button
                        key={p}
                        onClick={() => setPeriod(p)}
                        className={`px-2 py-1 text-xs rounded transition-colors ${
                          period === p ? 'bg-blue-600 text-white' : 'bg-slate-700 hover:bg-slate-600'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
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
            </div>
            <div className="h-96">
              <StockChart symbol={symbol || 'AAPL'} chartType={chartType} period={period} interval={interval} />
            </div>
          </div>

          {/* Technical Analysis - Enhanced */}
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Technical Analysis</h2>
            <div className="grid grid-cols-2 gap-6">
              {/* Momentum Indicators */}
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-3">Momentum Indicators</h3>
                <div className="space-y-2">
                  {/* RSI */}
                  {(technicals.rsi || aiInsight?.indicators.rsi_14) && (
                    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
                      <span className="text-sm text-slate-400">RSI (14)</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium">
                          {(technicals.rsi?.value ?? aiInsight?.indicators.rsi_14)?.toFixed(2)}
                        </span>
                        <span className={`text-xs ${getRsiSignal(technicals.rsi?.value ?? aiInsight?.indicators.rsi_14 ?? 50).color}`}>
                          {getRsiSignal(technicals.rsi?.value ?? aiInsight?.indicators.rsi_14 ?? 50).text}
                        </span>
                      </div>
                    </div>
                  )}
                  {/* MACD */}
                  {(technicals.macd || aiInsight?.indicators.macd) && (
                    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
                      <span className="text-sm text-slate-400">MACD</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium">
                          {(technicals.macd?.macd_line ?? aiInsight?.indicators.macd)?.toFixed(2)}
                        </span>
                        <span className={`text-xs ${(technicals.macd?.histogram ?? aiInsight?.indicators.macd_histogram ?? 0) > 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {(technicals.macd?.histogram ?? aiInsight?.indicators.macd_histogram ?? 0) > 0 ? 'Bullish' : 'Bearish'}
                        </span>
                      </div>
                    </div>
                  )}
                  {/* MACD Signal Line */}
                  {aiInsight?.indicators.macd_signal && (
                    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
                      <span className="text-sm text-slate-400">MACD Signal</span>
                      <span className="text-sm font-medium">{aiInsight.indicators.macd_signal.toFixed(2)}</span>
                    </div>
                  )}
                  {/* MACD Histogram */}
                  {aiInsight?.indicators.macd_histogram && (
                    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
                      <span className="text-sm text-slate-400">MACD Histogram</span>
                      <span className={`text-sm font-medium ${aiInsight.indicators.macd_histogram > 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {aiInsight.indicators.macd_histogram > 0 ? '+' : ''}{aiInsight.indicators.macd_histogram.toFixed(2)}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Moving Averages */}
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-3">Moving Averages</h3>
                <div className="space-y-2">
                  {/* SMA 20 */}
                  {(technicals.sma_20 || aiInsight?.indicators.sma_20) && (
                    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
                      <span className="text-sm text-slate-400">SMA (20)</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium">${(technicals.sma_20 ?? aiInsight?.indicators.sma_20)?.toFixed(2)}</span>
                        <span className={`text-xs ${aiInsight?.price_vs_ma?.above_sma_20 ? 'text-green-500' : 'text-red-500'}`}>
                          {aiInsight?.price_vs_ma?.above_sma_20 ? 'Above' : 'Below'}
                        </span>
                      </div>
                    </div>
                  )}
                  {/* SMA 50 */}
                  {aiInsight?.indicators.sma_50 && (
                    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
                      <span className="text-sm text-slate-400">SMA (50)</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium">${aiInsight.indicators.sma_50.toFixed(2)}</span>
                        <span className={`text-xs ${aiInsight.price_vs_ma?.above_sma_50 ? 'text-green-500' : 'text-red-500'}`}>
                          {aiInsight.price_vs_ma?.above_sma_50 ? 'Above' : 'Below'}
                        </span>
                      </div>
                    </div>
                  )}
                  {/* SMA 200 */}
                  {aiInsight?.indicators.sma_200 && (
                    <div className="flex items-center justify-between py-2 border-b border-slate-700/50">
                      <span className="text-sm text-slate-400">SMA (200)</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium">${aiInsight.indicators.sma_200.toFixed(2)}</span>
                        <span className={`text-xs ${aiInsight.price_vs_ma?.above_sma_200 ? 'text-green-500' : 'text-red-500'}`}>
                          {aiInsight.price_vs_ma?.above_sma_200 ? 'Above' : 'Below'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Volatility & Volume Row */}
            {aiInsight && (
              <div className="mt-4 pt-4 border-t border-slate-700">
                <h3 className="text-sm font-medium text-slate-400 mb-3">Volatility & Volume</h3>
                <div className="grid grid-cols-4 gap-4">
                  {/* ATR */}
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <p className="text-xs text-slate-400 mb-1">ATR (14)</p>
                    <p className="text-lg font-semibold">${aiInsight.indicators.atr_14?.toFixed(2)}</p>
                    <p className="text-xs text-slate-500">Avg True Range</p>
                  </div>
                  {/* Volume Ratio */}
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <p className="text-xs text-slate-400 mb-1">Volume Ratio</p>
                    <p className={`text-lg font-semibold ${aiInsight.indicators.volume_ratio > 1.5 ? 'text-yellow-400' : aiInsight.indicators.volume_ratio > 1 ? 'text-green-400' : 'text-slate-300'}`}>
                      {aiInsight.indicators.volume_ratio?.toFixed(2)}x
                    </p>
                    <p className="text-xs text-slate-500">vs 20-day avg</p>
                  </div>
                  {/* 1 Week Change */}
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <p className="text-xs text-slate-400 mb-1">1 Week</p>
                    <p className={`text-lg font-semibold ${aiInsight.momentum.week_change_pct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {aiInsight.momentum.week_change_pct >= 0 ? '+' : ''}{aiInsight.momentum.week_change_pct?.toFixed(1)}%
                    </p>
                    <p className="text-xs text-slate-500">Price change</p>
                  </div>
                  {/* 1 Month Change */}
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <p className="text-xs text-slate-400 mb-1">1 Month</p>
                    <p className={`text-lg font-semibold ${aiInsight.momentum.month_change_pct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {aiInsight.momentum.month_change_pct >= 0 ? '+' : ''}{aiInsight.momentum.month_change_pct?.toFixed(1)}%
                    </p>
                    <p className="text-xs text-slate-500">Price change</p>
                  </div>
                </div>
              </div>
            )}

            {/* Overall Signal Summary */}
            {aiInsight && (
              <div className="mt-4 pt-4 border-t border-slate-700">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-slate-400">Overall Signal:</span>
                    <span className={`text-sm font-bold px-3 py-1 rounded ${
                      aiInsight.score >= 70 ? 'bg-green-600 text-white' :
                      aiInsight.score >= 50 ? 'bg-yellow-500 text-black' :
                      'bg-red-600 text-white'
                    }`}>
                      {aiInsight.recommendation}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">Score:</span>
                    <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${aiInsight.score >= 70 ? 'bg-green-500' : aiInsight.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                        style={{ width: `${aiInsight.score}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium">{aiInsight.score}</span>
                  </div>
                </div>
              </div>
            )}
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

          {/* Pattern Detection - Bull/Bear Flags, Breakouts, etc. */}
          <PatternInsights symbol={symbol || 'AAPL'} interval={interval} />

          {/* Multi-Timeframe AI Insight */}
          <MultiTimeframeInsight symbol={symbol || 'AAPL'} />

          {/* Triple Screen Analysis (Elder's System) */}
          <TripleScreenPanel symbol={symbol || 'AAPL'} />

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

          {/* NOTE: Elliott Wave is now part of MultiTimeframeInsight component above with tabbed 15min/1hour/daily views */}

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
