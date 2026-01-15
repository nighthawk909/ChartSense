import { useEffect, useRef } from 'react'
import { createChart, ColorType, IChartApi } from 'lightweight-charts'

interface StockChartProps {
  symbol: string
}

// Generate mock candlestick data
function generateMockData() {
  const data = []
  let time = new Date('2024-01-01').getTime() / 1000
  let open = 150

  for (let i = 0; i < 100; i++) {
    const volatility = Math.random() * 5
    const change = (Math.random() - 0.5) * volatility
    const high = open + Math.abs(change) + Math.random() * 2
    const low = open - Math.abs(change) - Math.random() * 2
    const close = open + change

    data.push({
      time: time as number,
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
    })

    open = close
    time += 86400 // Add one day
  }

  return data
}

export default function StockChart({ symbol }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

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
        vertLine: {
          color: '#64748b',
          labelBackgroundColor: '#1e293b',
        },
        horzLine: {
          color: '#64748b',
          labelBackgroundColor: '#1e293b',
        },
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
      },
      rightPriceScale: {
        borderColor: '#334155',
      },
    })

    chartRef.current = chart

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderDownColor: '#ef4444',
      borderUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      wickUpColor: '#22c55e',
    })

    // Set mock data
    const mockData = generateMockData()
    candlestickSeries.setData(mockData)

    // Add volume series
    const volumeSeries = chart.addHistogramSeries({
      color: '#3b82f6',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    })

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    })

    const volumeData = mockData.map((d) => ({
      time: d.time,
      value: Math.random() * 10000000 + 1000000,
      color: d.close >= d.open ? '#22c55e40' : '#ef444440',
    }))

    volumeSeries.setData(volumeData)

    // Fit content
    chart.timeScale().fitContent()

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [symbol])

  return <div ref={chartContainerRef} className="w-full" />
}
