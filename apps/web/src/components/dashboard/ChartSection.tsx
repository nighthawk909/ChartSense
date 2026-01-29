import StockChart from '../StockChart'
import { TimeInterval, intervals, periods } from '../../hooks/useDashboardData'

interface ChartSectionProps {
  selectedStock: string
  selectedPeriod: string
  setSelectedPeriod: (period: string) => void
  selectedInterval: TimeInterval
  setSelectedInterval: (interval: TimeInterval) => void
}

export default function ChartSection({
  selectedStock,
  selectedPeriod,
  setSelectedPeriod,
  selectedInterval,
  setSelectedInterval,
}: ChartSectionProps) {
  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-4">
        <h2 className="text-lg font-semibold">{selectedStock} Chart</h2>
        <div className="flex flex-wrap gap-2 sm:gap-4">
          {/* Interval selector */}
          <div className="flex flex-wrap gap-1 bg-slate-900 rounded-lg p-1">
            {intervals.map((int) => (
              <button
                key={int.value}
                onClick={() => setSelectedInterval(int.value)}
                className={`px-2 py-1 text-xs rounded transition-colors whitespace-nowrap ${
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
          <div className="flex flex-wrap gap-1">
            {periods.map((period) => (
              <button
                key={period}
                onClick={() => setSelectedPeriod(period)}
                className={`px-2 sm:px-3 py-1 text-xs sm:text-sm rounded transition-colors whitespace-nowrap ${
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
          enableRealTime={true}
        />
      </div>
    </div>
  )
}
