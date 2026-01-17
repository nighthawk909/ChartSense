import { useEffect, useRef, useState, useCallback } from 'react'
import { createChart, ColorType, IChartApi, UTCTimestamp, ISeriesApi, CandlestickData, HistogramData } from 'lightweight-charts'
import { RefreshCw, AlertTriangle, Clock, Wifi, WifiOff } from 'lucide-react'
import { useRealTimeData, BarData } from '../hooks/useRealTimeData'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Threshold for stale data - if chart is more than this many seconds behind, trigger hardReset
const STALE_THRESHOLD_SECONDS = 65

type TimeInterval = '1min' | '5min' | '15min' | '30min' | '60min' | 'daily' | 'weekly' | 'monthly'

interface StockChartProps {
  symbol: string
  chartType?: 'candlestick' | 'line'
  period?: string
  interval?: TimeInterval
  showRefreshButton?: boolean
  autoRefreshSeconds?: number // Auto-refresh interval in seconds (0 = disabled)
  enableRealTime?: boolean // Enable WebSocket real-time updates (default: true for intraday)
}

interface HistoricalData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

// Convert date string to timestamp for lightweight-charts
// Handles both "YYYY-MM-DD" and ISO "YYYY-MM-DDTHH:MM:SSZ" formats
const parseTimestamp = (dateStr: string): UTCTimestamp => {
  // For ISO timestamps (intraday), convert to Unix seconds
  if (dateStr.includes('T')) {
    return Math.floor(new Date(dateStr).getTime() / 1000) as UTCTimestamp
  }
  // For date-only strings (daily), return as-is (lightweight-charts accepts YYYY-MM-DD)
  return dateStr as unknown as UTCTimestamp
}

export default function StockChart({
  symbol,
  chartType = 'candlestick',
  period = '1M',
  interval = 'daily',
  showRefreshButton = true,
  autoRefreshSeconds = 0,
  enableRealTime = true,
}: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const lineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [dataPoints, setDataPoints] = useState<number>(0)
  const [chartData, setChartData] = useState<HistoricalData[] | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [dataAge, setDataAge] = useState<string | null>(null)
  const [isStale, setIsStale] = useState(false)
  const [lastDataTimestamp, setLastDataTimestamp] = useState<number>(0)
  const fetchCountRef = useRef(0)
  const hardResetTriggeredRef = useRef(false)

  // Determine if real-time should be enabled (only for intraday intervals)
  const isIntraday = ['1min', '5min', '15min', '30min', '60min'].includes(interval)
  const shouldUseRealTime = enableRealTime && isIntraday

  // WebSocket real-time data hook
  const { latestBar, status: wsStatus, forceRefresh: wsForceRefresh, isConnected } = useRealTimeData(
    shouldUseRealTime ? symbol : ''
  )

  // Filter data based on period
  const filterByPeriod = (data: HistoricalData[], period: string): HistoricalData[] => {
    const now = new Date()
    let cutoffDate: Date

    switch (period) {
      case '1D':
        cutoffDate = new Date(now.getTime() - 1 * 24 * 60 * 60 * 1000)
        break
      case '1W':
        cutoffDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        break
      case '1M':
        cutoffDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
        break
      case '3M':
        cutoffDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
        break
      case '1Y':
        cutoffDate = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000)
        break
      case 'ALL':
      default:
        return data
    }

    return data.filter(item => new Date(item.date) >= cutoffDate)
  }

  // Hard reset - completely destroy and recreate chart with fresh data
  const hardReset = useCallback(async () => {
    console.log('[StockChart] Triggering hardReset for stale data')
    hardResetTriggeredRef.current = true

    // Destroy existing chart
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      lineSeriesRef.current = null
      volumeSeriesRef.current = null
    }

    // Clear state
    setChartData(null)
    setLoading(true)
    setIsStale(false)

    // Force WebSocket refresh
    if (shouldUseRealTime) {
      wsForceRefresh()
    }

    // Fetch fresh data
    await fetchData(true)
    hardResetTriggeredRef.current = false
  }, [shouldUseRealTime, wsForceRefresh])

  // Fetch data function - can be called manually for force refresh
  const fetchData = useCallback(async (isRefresh = false) => {
    const currentFetchId = ++fetchCountRef.current

    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
      setChartData(null)
    }
    setError(null)

    try {
      const outputsize = ['1Y', 'ALL'].includes(period) ? 'full' : 'compact'
      // Add cache-busting timestamp for force refresh
      const cacheBuster = isRefresh ? `&_t=${Date.now()}` : ''

      // Also call force-refresh endpoint if this is a manual refresh
      if (isRefresh) {
        try {
          await fetch(`${API_URL}/api/stocks/force-refresh/${symbol}`, { method: 'POST' })
        } catch (e) {
          console.warn('[StockChart] Force refresh endpoint not available:', e)
        }
      }

      const response = await fetch(`${API_URL}/api/stocks/history/${symbol}?outputsize=${outputsize}&interval=${interval}${cacheBuster}`)

      if (!response.ok) throw new Error('Failed to fetch stock data')

      const data = await response.json()
      if (!data.history || data.history.length === 0) {
        throw new Error('No historical data available')
      }

      // Check if this fetch is still current
      if (currentFetchId !== fetchCountRef.current) return

      // Filter and sort
      let filteredData = filterByPeriod(data.history, period)

      // If no data for selected period (e.g., before market open), show most recent available data
      if (filteredData.length === 0 && data.history.length > 0) {
        // For intraday intervals, show most recent day's data
        const sortedHistory = [...data.history].sort((a: HistoricalData, b: HistoricalData) =>
          new Date(b.date).getTime() - new Date(a.date).getTime()
        )
        // Get the most recent date and filter to that day
        const mostRecentDate = new Date(sortedHistory[0].date).toDateString()
        filteredData = data.history.filter((item: HistoricalData) =>
          new Date(item.date).toDateString() === mostRecentDate
        )
      }

      // For intraday intervals (1m, 5m, 15m, etc.), ensure we show the most recent trading session
      // This handles cases where 1D period filter returns old data from a previous session
      if (isIntraday && filteredData.length > 0) {
        const sortedFiltered = [...filteredData].sort((a: HistoricalData, b: HistoricalData) =>
          new Date(b.date).getTime() - new Date(a.date).getTime()
        )
        const mostRecentTimestamp = new Date(sortedFiltered[0].date)
        const now = new Date()
        const ageHours = (now.getTime() - mostRecentTimestamp.getTime()) / (1000 * 60 * 60)

        // If data is more than 24 hours old AND we have more recent data in the full history
        if (ageHours > 24 && data.history.length > filteredData.length) {
          console.log(`[StockChart] Intraday data ${ageHours.toFixed(1)}h old, using most recent session from full history`)
          const fullSortedHistory = [...data.history].sort((a: HistoricalData, b: HistoricalData) =>
            new Date(b.date).getTime() - new Date(a.date).getTime()
          )
          const newestDate = new Date(fullSortedHistory[0].date).toDateString()
          filteredData = data.history.filter((item: HistoricalData) =>
            new Date(item.date).toDateString() === newestDate
          )
        }
      }

      const sortedData = [...filteredData].sort((a: HistoricalData, b: HistoricalData) =>
        new Date(a.date).getTime() - new Date(b.date).getTime()
      )

      if (sortedData.length === 0) {
        throw new Error('No historical data available')
      }

      // Check data freshness - calculate age of most recent data point
      const mostRecentDataPoint = sortedData[sortedData.length - 1]
      const dataTimestamp = new Date(mostRecentDataPoint.date)
      const now = new Date()
      const ageMs = now.getTime() - dataTimestamp.getTime()
      const ageSeconds = Math.floor(ageMs / 1000)
      const ageMinutes = Math.floor(ageSeconds / 60)
      const ageHours = Math.floor(ageMinutes / 60)
      const ageDays = Math.floor(ageHours / 24)

      // Store timestamp for stale detection
      setLastDataTimestamp(dataTimestamp.getTime())

      // Format age string - for user display only
      // We no longer show "stale" warnings since:
      // - Daily/weekly charts naturally lag by hours (market close data)
      // - The user can always manually refresh if they want fresher data
      let ageStr = ''

      if (ageDays > 0) {
        ageStr = `${ageDays}d ago`
      } else if (ageHours > 0) {
        ageStr = `${ageHours}h ago`
      } else if (ageMinutes > 0) {
        ageStr = `${ageMinutes}m ago`
      } else {
        ageStr = 'Just now'
      }
      setDataAge(ageStr)
      // Never mark as stale - we trust the data source is providing what's available
      // User can always click refresh to get latest data
      setIsStale(false)

      // Auto-trigger hardReset if data is critically stale (>65 seconds for intraday)
      if (isIntraday && ageSeconds > STALE_THRESHOLD_SECONDS && !hardResetTriggeredRef.current) {
        console.warn(`[StockChart] Data is ${ageSeconds}s old (>${STALE_THRESHOLD_SECONDS}s threshold), triggering hardReset`)
        // Don't await here to avoid blocking
        setTimeout(() => hardReset(), 100)
      }

      setChartData(sortedData)
      setLastUpdated(new Date())
      setDataPoints(sortedData.length)
    } catch (err) {
      if (currentFetchId === fetchCountRef.current) {
        console.error('[StockChart] Chart error:', err)
        setError(err instanceof Error ? err.message : 'Failed to load chart')
      }
    } finally {
      if (currentFetchId === fetchCountRef.current) {
        setLoading(false)
        setRefreshing(false)
      }
    }
  }, [symbol, period, interval, isIntraday, hardReset])

  // Force refresh handler
  const handleForceRefresh = useCallback(() => {
    if (shouldUseRealTime) {
      wsForceRefresh()
    }
    fetchData(true)
  }, [fetchData, shouldUseRealTime, wsForceRefresh])

  // Effect 1: Fetch data on mount and when dependencies change
  useEffect(() => {
    fetchData(false)
  }, [fetchData])

  // Effect for auto-refresh
  useEffect(() => {
    if (autoRefreshSeconds <= 0) return

    const intervalId = setInterval(() => {
      fetchData(true)
    }, autoRefreshSeconds * 1000)

    return () => clearInterval(intervalId)
  }, [autoRefreshSeconds, fetchData])

  // Effect: Update chart with real-time WebSocket data
  useEffect(() => {
    if (!latestBar || !chartRef.current) return
    if (!shouldUseRealTime) return

    const bar = latestBar as BarData

    // Update candlestick series
    if (candleSeriesRef.current && chartType === 'candlestick') {
      const candleData: CandlestickData = {
        time: bar.time as UTCTimestamp,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }
      candleSeriesRef.current.update(candleData)
    }

    // Update line series
    if (lineSeriesRef.current && chartType === 'line') {
      lineSeriesRef.current.update({
        time: bar.time as UTCTimestamp,
        value: bar.close,
      })
    }

    // Update volume series
    if (volumeSeriesRef.current) {
      const volumeData: HistogramData = {
        time: bar.time as UTCTimestamp,
        value: bar.volume,
        color: bar.close >= bar.open ? '#22c55e40' : '#ef444440',
      }
      volumeSeriesRef.current.update(volumeData)
    }

    // Update timestamp tracking
    setLastDataTimestamp(bar.time * 1000)
    setLastUpdated(new Date())
    setIsStale(false)
    setDataAge('Live')
  }, [latestBar, chartType, shouldUseRealTime])

  // Effect: Monitor for stale data and trigger hardReset
  useEffect(() => {
    if (!shouldUseRealTime || !lastDataTimestamp) return

    const checkStale = () => {
      const now = Date.now()
      const ageSeconds = Math.floor((now - lastDataTimestamp) / 1000)

      if (ageSeconds > STALE_THRESHOLD_SECONDS && !hardResetTriggeredRef.current) {
        console.warn(`[StockChart] Stale data detected: ${ageSeconds}s behind. Triggering hardReset.`)
        hardReset()
      }
    }

    // Check every 10 seconds
    const intervalId = setInterval(checkStale, 10000)
    return () => clearInterval(intervalId)
  }, [shouldUseRealTime, lastDataTimestamp, hardReset])

  // Effect 2: Create/update chart when data is ready
  useEffect(() => {
    if (!chartContainerRef.current || !chartData || chartData.length === 0) return

    // Clean up previous chart
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
    }

    // Create new chart
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
      height: 350,
      crosshair: {
        vertLine: { color: '#64748b', labelBackgroundColor: '#1e293b' },
        horzLine: { color: '#64748b', labelBackgroundColor: '#1e293b' },
      },
      timeScale: { borderColor: '#334155', timeVisible: true },
      rightPriceScale: { borderColor: '#334155' },
    })

    chartRef.current = chart

    // Add data series
    if (chartType === 'candlestick') {
      const series = chart.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderDownColor: '#ef4444',
        borderUpColor: '#22c55e',
        wickDownColor: '#ef4444',
        wickUpColor: '#22c55e',
      })
      series.setData(chartData.map((d: HistoricalData) => ({
        time: parseTimestamp(d.date),
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      })))
      candleSeriesRef.current = series
    } else {
      const series = chart.addLineSeries({ color: '#3b82f6', lineWidth: 2 })
      series.setData(chartData.map((d: HistoricalData) => ({
        time: parseTimestamp(d.date),
        value: d.close,
      })))
      lineSeriesRef.current = series
    }

    // Volume
    const volumeSeries = chart.addHistogramSeries({
      color: '#3b82f6',
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    })
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })
    volumeSeries.setData(chartData.map((d: HistoricalData) => ({
      time: parseTimestamp(d.date),
      value: d.volume,
      color: d.close >= d.open ? '#22c55e40' : '#ef444440',
    })))
    volumeSeriesRef.current = volumeSeries

    chart.timeScale().fitContent()

    // Resize handler
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [chartData, chartType])

  const formatLastUpdated = () => {
    if (!lastUpdated) return ''
    const now = new Date()
    const diffSeconds = Math.floor((now.getTime() - lastUpdated.getTime()) / 1000)
    if (diffSeconds < 60) return `${diffSeconds}s ago`
    const diffMinutes = Math.floor(diffSeconds / 60)
    if (diffMinutes < 60) return `${diffMinutes}m ago`
    return lastUpdated.toLocaleTimeString()
  }

  return (
    <div className="w-full">
      {/* Real-time connection status for intraday */}
      {shouldUseRealTime && (
        <div className={`flex items-center gap-2 mb-2 px-2 py-1 rounded text-xs ${
          isConnected ? 'bg-green-500/10 text-green-400' : 'bg-slate-700/50 text-slate-400'
        }`}>
          {isConnected ? (
            <>
              <Wifi className="w-3 h-3" />
              <span>Live WebSocket Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-3 h-3" />
              <span>WebSocket {wsStatus} - Using REST fallback</span>
            </>
          )}
        </div>
      )}

      {/* Stale data warning */}
      {isStale && !loading && chartData && (
        <div className="flex items-center gap-2 mb-2 px-2 py-1.5 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-yellow-400 text-xs">
          <AlertTriangle className="w-4 h-4" />
          <span>Data appears stale ({dataAge}). Click refresh to get latest data.</span>
          <button
            onClick={handleForceRefresh}
            disabled={refreshing}
            className="ml-auto flex items-center gap-1 px-2 py-1 bg-yellow-500/20 hover:bg-yellow-500/30 rounded transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="w-full h-[350px] flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="w-full h-[350px] flex flex-col items-center justify-center text-red-400 gap-3">
          <AlertTriangle className="w-8 h-8" />
          <p>{error}</p>
          <button
            onClick={handleForceRefresh}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      )}

      {/* Chart container - only rendered when we have data */}
      {!loading && !error && chartData && (
        <>
          <div ref={chartContainerRef} className="w-full" />
          {lastUpdated && (
            <div className="flex items-center justify-between mt-2 px-1 text-xs text-slate-500">
              <div className="flex items-center gap-2">
                <span>{dataPoints} data points</span>
                {dataAge && (
                  <span className={`flex items-center gap-1 ${dataAge === 'Live' || dataAge === 'Just now' ? 'text-green-400' : 'text-slate-500'}`}>
                    <Clock className="w-3 h-3" />
                    {dataAge}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${dataAge === 'Live' || dataAge === 'Just now' ? 'bg-green-500' : 'bg-blue-500'} animate-pulse`}></span>
                  <span>Updated {formatLastUpdated()}</span>
                </div>
                {showRefreshButton && (
                  <button
                    onClick={handleForceRefresh}
                    disabled={refreshing}
                    className="p-1 hover:bg-slate-700 rounded transition-colors"
                    title="Force refresh data"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-blue-400' : 'text-slate-400 hover:text-white'}`} />
                  </button>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
