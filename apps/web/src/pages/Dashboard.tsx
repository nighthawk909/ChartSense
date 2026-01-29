import { RefreshCw, AlertCircle, BarChart3 } from 'lucide-react'
import { useDashboardData } from '../hooks/useDashboardData'
import MarketOverview from '../components/dashboard/MarketOverview'
import ChartSection from '../components/dashboard/ChartSection'
import WatchlistPanel from '../components/dashboard/WatchlistPanel'
import IndicatorsSection from '../components/dashboard/IndicatorsSection'
import PerformanceDashboard from '../components/dashboard/PerformanceDashboard'

export default function Dashboard() {
  const {
    selectedStock,
    setSelectedStock,
    selectedPeriod,
    setSelectedPeriod,
    selectedInterval,
    setSelectedInterval,
    watchlist,
    positions,
    indices,
    indicators,
    lastUpdated,
    loading,
    error,
    refreshing,
    indicatorsLoading,
    showPerformance,
    setShowPerformance,
    handleRefresh,
  } = useDashboardData()

  return (
    <div className="space-y-6">
      {/* Header with timestamp and refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <div className="flex items-center gap-3 mt-1">
            {lastUpdated && (
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                <span className="text-sm text-green-400">
                  Live data updated: {lastUpdated.toLocaleTimeString()}
                </span>
              </div>
            )}
            {loading && (
              <span className="text-sm text-slate-400">Loading...</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPerformance(!showPerformance)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              showPerformance ? 'bg-blue-600 text-white' : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            Performance
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Performance Dashboard (collapsible) */}
      {showPerformance && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <PerformanceDashboard compact />
        </div>
      )}

      {/* Market Overview */}
      <MarketOverview indices={indices} />

      {/* Chart and Watchlist */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <ChartSection
            selectedStock={selectedStock}
            selectedPeriod={selectedPeriod}
            setSelectedPeriod={setSelectedPeriod}
            selectedInterval={selectedInterval}
            setSelectedInterval={setSelectedInterval}
          />
        </div>
        <div>
          <WatchlistPanel
            watchlist={watchlist}
            positions={positions}
            selectedStock={selectedStock}
            setSelectedStock={setSelectedStock}
          />
        </div>
      </div>

      {/* Technical Indicators */}
      <IndicatorsSection
        selectedStock={selectedStock}
        indicators={indicators}
        indicatorsLoading={indicatorsLoading}
      />
    </div>
  )
}
