import { useEffect, useRef, useState, useCallback } from 'react'
import { createChart, ColorType, IChartApi, UTCTimestamp } from 'lightweight-charts'
import { RefreshCw, AlertTriangle } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type TimeInterval = '1Min' | '5Min' | '15Min' | '1Hour' | '1Day'

interface CryptoChartProps {
  symbol: string
  chartType?: 'candlestick' | 'line'
  timeframe?: TimeInterval
}

interface BarData {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

// Stale threshold in seconds by timeframe
const STALE_THRESHOLDS: Record<TimeInterval, number> = {
  '1Min': 120,   // 2 minutes for 1-min chart
  '5Min': 600,   // 10 minutes for 5-min chart
  '15Min': 1800, // 30 minutes for 15-min chart
  '1Hour': 7200, // 2 hours for hourly chart
  '1Day': 86400, // 1 day for daily chart
}

export default function CryptoChart({ symbol, chartType = 'candlestick', timeframe = '1Hour' }: CryptoChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [dataPoints, setDataPoints] = useState<number>(0)
  const [lastBarTime, setLastBarTime] = useState<Date | null>(null)
  const [isStale, setIsStale] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)  // Used to force chart recreation

  useEffect(() => {
    if (!chartContainerRef.current) return

    let isCleanedUp = false

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 300,
      crosshair: {
        vertLine: { color: '#64748b', labelBackgroundColor: '#1e293b' },
        horzLine: { color: '#64748b', labelBackgroundColor: '#1e293b' },
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
        // The chart displays timestamps in local timezone automatically
        // UTC timestamps from API are converted to local time for display
      },
      rightPriceScale: { borderColor: '#334155' },
    })

    chartRef.current = chart

    // Load data
    const loadChart = async () => {
      setLoading(true)
      setError(null)

      try {
        // Remove slash from symbol for API call (BTC/USD -> BTCUSD)
        const apiSymbol = symbol.replace('/', '')

        // Determine appropriate limit based on timeframe
        // Larger timeframes need more historical data to be useful
        const limitByTimeframe: Record<TimeInterval, number> = {
          '1Min': 100,    // ~1.6 hours of 1-min bars
          '5Min': 100,    // ~8 hours of 5-min bars
          '15Min': 100,   // ~25 hours of 15-min bars
          '1Hour': 168,   // 1 week of hourly bars
          '1Day': 365,    // 1 year of daily bars
        }
        const limit = limitByTimeframe[timeframe] || 100

        const response = await fetch(`${API_URL}/api/crypto/bars/${apiSymbol}?timeframe=${timeframe}&limit=${limit}`)

        if (!response.ok) throw new Error('Failed to fetch crypto data')

        const data = await response.json()
        if (!data.bars || data.bars.length === 0) {
          throw new Error('No historical data available')
        }

        // Check if component was unmounted during fetch
        if (isCleanedUp) return

        // Sort by timestamp
        const sortedData = [...data.bars].sort((a: BarData, b: BarData) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        )

        // Track data freshness
        setLastUpdated(new Date())
        setDataPoints(sortedData.length)

        // Check last bar time for staleness detection
        if (sortedData.length > 0) {
          const lastBar = sortedData[sortedData.length - 1]
          const lastTime = new Date(lastBar.timestamp)
          setLastBarTime(lastTime)

          // Check if data is stale
          const now = new Date()
          const ageSeconds = (now.getTime() - lastTime.getTime()) / 1000
          const threshold = STALE_THRESHOLDS[timeframe] || 3600
          setIsStale(ageSeconds > threshold)
        }

        if (chartType === 'candlestick') {
          const series = chart.addCandlestickSeries({
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderDownColor: '#ef4444',
            borderUpColor: '#22c55e',
            wickDownColor: '#ef4444',
            wickUpColor: '#22c55e',
          })
          series.setData(sortedData.map((d: BarData) => ({
            time: Math.floor(new Date(d.timestamp).getTime() / 1000) as UTCTimestamp,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
          })))
        } else {
          const series = chart.addLineSeries({ color: '#3b82f6', lineWidth: 2 })
          series.setData(sortedData.map((d: BarData) => ({
            time: Math.floor(new Date(d.timestamp).getTime() / 1000) as UTCTimestamp,
            value: d.close,
          })))
        }

        // Volume
        const volumeSeries = chart.addHistogramSeries({
          color: '#3b82f6',
          priceFormat: { type: 'volume' },
          priceScaleId: '',
        })
        volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })
        volumeSeries.setData(sortedData.map((d: BarData) => ({
          time: Math.floor(new Date(d.timestamp).getTime() / 1000) as UTCTimestamp,
          value: d.volume,
          color: d.close >= d.open ? '#22c55e40' : '#ef444440',
        })))

        chart.timeScale().fitContent()
      } catch (err) {
        if (isCleanedUp) return
        console.error('Crypto chart error:', err)
        setError(err instanceof Error ? err.message : 'Failed to load chart')
      } finally {
        if (!isCleanedUp) {
          setLoading(false)
        }
      }
    }

    loadChart()

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      isCleanedUp = true
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [symbol, chartType, timeframe, refreshKey])  // Include refreshKey to trigger recreation

  // Handle manual refresh - forces chart recreation with fresh data
  const handleRefresh = useCallback(() => {
    if (refreshing) return
    setRefreshing(true)
    setIsStale(false)
    setError(null)
    // Increment refreshKey to trigger useEffect to recreate chart with new data
    setRefreshKey(prev => prev + 1)
    // Reset refreshing state after a short delay
    setTimeout(() => setRefreshing(false), 500)
  }, [refreshing])

  return (
    <div className="w-full">
      {/* Chart container - always rendered so ref is available */}
      <div
        ref={chartContainerRef}
        className="w-full"
        style={{ display: loading || error ? 'none' : 'block' }}
      />

      {/* Loading state */}
      {loading && (
        <div className="w-full h-[300px] flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="w-full h-[300px] flex items-center justify-center text-red-400">
          <p>{error}</p>
        </div>
      )}

      {/* Data freshness indicator with refresh button */}
      {!loading && !error && lastUpdated && (
        <div className="space-y-2 mt-2">
          {/* Stale data warning */}
          {isStale && (
            <div className="flex items-center justify-between px-2 py-1.5 bg-yellow-500/10 border border-yellow-500/30 rounded text-xs">
              <div className="flex items-center gap-1.5 text-yellow-400">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Chart data may be outdated</span>
              </div>
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-1 px-2 py-0.5 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 rounded text-[10px] font-medium"
              >
                <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          )}

          {/* Data info bar */}
          <div className="flex items-center justify-between px-1 text-xs text-slate-500">
            <span>{dataPoints} data points</span>
            <div className="flex items-center gap-2">
              {lastBarTime && (
                <span className="text-slate-600">
                  Last bar: {lastBarTime.toLocaleTimeString()}
                </span>
              )}
              <div className="flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${isStale ? 'bg-yellow-500' : 'bg-green-500 animate-pulse'}`}></span>
                <span>Fetched {lastUpdated.toLocaleTimeString()}</span>
              </div>
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="p-1 hover:bg-slate-700 rounded transition-colors"
                title="Refresh chart data"
              >
                <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
