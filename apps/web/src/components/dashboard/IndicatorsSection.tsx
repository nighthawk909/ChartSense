import { RefreshCw } from 'lucide-react'
import { TechnicalIndicators } from '../../hooks/useDashboardData'
import { getStatusColor } from '../../utils/dashboard-helpers'

interface IndicatorsSectionProps {
  selectedStock: string
  indicators: TechnicalIndicators | null
  indicatorsLoading: boolean
}

interface IndicatorCardProps {
  name: string
  value: number | string
  status: string
  statusColor: string
}

function IndicatorCard({ name, value, status, statusColor }: IndicatorCardProps) {
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

export default function IndicatorsSection({
  selectedStock,
  indicators,
  indicatorsLoading,
}: IndicatorsSectionProps) {
  return (
    <section>
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Technical Indicators - {selectedStock}</h2>
          {indicatorsLoading && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <RefreshCw className="w-4 h-4 animate-spin" />
              Loading...
            </div>
          )}
        </div>
        <div className="grid grid-cols-4 gap-4">
          <IndicatorCard
            name="RSI (14)"
            value={indicators?.rsi_14?.value ?? '--'}
            status={indicators?.rsi_14?.signal ?? 'Loading'}
            statusColor={getStatusColor(indicators?.rsi_14?.signal)}
          />
          <IndicatorCard
            name="MACD"
            value={indicators?.macd?.value ?? '--'}
            status={indicators?.macd?.signal ?? 'Loading'}
            statusColor={getStatusColor(indicators?.macd?.signal)}
          />
          <IndicatorCard
            name="SMA (50)"
            value={indicators?.sma_50?.value ?? '--'}
            status={indicators?.sma_50?.signal ?? 'Loading'}
            statusColor={getStatusColor(indicators?.sma_50?.signal)}
          />
          <IndicatorCard
            name="Bollinger Bands"
            value={indicators?.bollinger?.position ?? 'Middle'}
            status={indicators?.bollinger?.signal ?? 'Neutral'}
            statusColor={getStatusColor(indicators?.bollinger?.signal)}
          />
        </div>
      </div>
    </section>
  )
}
