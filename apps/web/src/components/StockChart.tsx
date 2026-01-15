import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, LineData, HistogramData } from 'lightweight-charts'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface StockChartProps {
  symbol: string
  chartType?: 'candlestick' | 'line'
  period?: string
}

interface HistoricalData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export default function StockChart({ symbol, chartType = 'candlestick', period = '1M' }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
      height: 350,
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
        const outputsize = ['1Y', 'ALL'].includes(period) ? 'full' : 'compact'
        const response = await fetch(`${API_URL}/api/stocks/history/${symbol}?outputsize=${outputsize}`)

        if (!response.ok) throw new Error('Failed to fetch stock data')

        const data = await response.json()
        if (!data.history || data.history.length === 0) {
          throw new Error('No historical data available')
        }

        // Filter and sort
        const filteredData = filterByPeriod(data.history, period)
        const sortedData = [...filteredData].sort((a: HistoricalData, b: HistoricalData) =>
          new Date(a.date).getTime() - new Date(b.date).getTime()
        )

        if (sortedData.length === 0) {
          throw new Error('No data for selected period')
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
          series.setData(sortedData.map((d: HistoricalData) => ({
            time: d.date,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
          })))
        } else {
          const series = chart.addLineSeries({ color: '#3b82f6', lineWidth: 2 })
          series.setData(sortedData.map((d: HistoricalData) => ({
            time: d.date,
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
        volumeSeries.setData(sortedData.map((d: HistoricalData) => ({
          time: d.date,
          value: d.volume,
          color: d.close >= d.open ? '#22c55e40' : '#ef444440',
        })))

        chart.timeScale().fitContent()
      } catch (err) {
        console.error('Chart error:', err)
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
  }, [symbol, chartType, period])

  if (loading) {
    return (
      <div className="w-full h-[350px] flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="w-full h-[350px] flex items-center justify-center text-red-400">
        <p>{error}</p>
      </div>
    )
  }

  return <div ref={chartContainerRef} className="w-full" />
}
