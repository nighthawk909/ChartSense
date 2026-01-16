import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, IChartApi, UTCTimestamp } from 'lightweight-charts'

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

export default function CryptoChart({ symbol, chartType = 'candlestick', timeframe = '1Hour' }: CryptoChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [dataPoints, setDataPoints] = useState<number>(0)

  useEffect(() => {
    if (!chartContainerRef.current) return

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
      timeScale: { borderColor: '#334155', timeVisible: true },
      rightPriceScale: { borderColor: '#334155' },
    })

    chartRef.current = chart

    // Load data
    const loadChart = async () => {
      setLoading(true)
      setError(null)

      try {
        const response = await fetch(`${API_URL}/api/crypto/bars/${encodeURIComponent(symbol)}?timeframe=${timeframe}&limit=100`)

        if (!response.ok) throw new Error('Failed to fetch crypto data')

        const data = await response.json()
        if (!data.bars || data.bars.length === 0) {
          throw new Error('No historical data available')
        }

        // Sort by timestamp
        const sortedData = [...data.bars].sort((a: BarData, b: BarData) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        )

        // Track data freshness
        setLastUpdated(new Date())
        setDataPoints(sortedData.length)

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
        console.error('Crypto chart error:', err)
        setError(err instanceof Error ? err.message : 'Failed to load chart')
      } finally {
        setLoading(false)
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
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [symbol, chartType, timeframe])

  if (loading) {
    return (
      <div className="w-full h-[300px] flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="w-full h-[300px] flex items-center justify-center text-red-400">
        <p>{error}</p>
      </div>
    )
  }

  return (
    <div className="w-full">
      <div ref={chartContainerRef} className="w-full" />
      {lastUpdated && (
        <div className="flex items-center justify-between mt-2 px-1 text-xs text-slate-500">
          <span>{dataPoints} data points</span>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span>Updated {lastUpdated.toLocaleTimeString()}</span>
          </div>
        </div>
      )}
    </div>
  )
}
