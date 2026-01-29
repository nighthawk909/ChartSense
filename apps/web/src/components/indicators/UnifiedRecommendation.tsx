import { useState, useEffect } from 'react'
import { Shield, AlertTriangle, TrendingUp, TrendingDown, Minus, Loader2, RefreshCw, ChevronDown, ChevronUp, Info } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface SourceBreakdown {
  source: string
  signal: string
  score: number
  weight: number
  contribution: number
  details?: string
}

interface UnifiedRecommendationData {
  symbol: string
  final_recommendation: string
  confidence: number
  composite_score: number
  risk_level: string
  action_summary: string
  sources: SourceBreakdown[]
  conflicts: string[]
  timestamp: string
}

interface Props {
  symbol: string
  interval?: string
}

export default function UnifiedRecommendation({ symbol, interval = '1hour' }: Props) {
  const [data, setData] = useState<UnifiedRecommendationData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const fetchUnifiedRecommendation = async () => {
    if (!symbol) return
    try {
      const response = await fetch(`${API_URL}/api/analysis/unified/${symbol}?interval=${interval}`)
      if (response.ok) {
        const result = await response.json()
        setData(result)
        setError(null)
      } else {
        setError('Failed to fetch unified recommendation')
      }
    } catch (err) {
      console.error('Failed to fetch unified recommendation:', err)
      setError('Unable to load recommendation')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    setLoading(true)
    fetchUnifiedRecommendation()
  }, [symbol, interval])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchUnifiedRecommendation()
  }

  if (loading) {
    return (
      <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-lg p-4 border border-slate-700">
        <div className="flex items-center justify-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin text-blue-400" />
          <span className="text-slate-400">Analyzing all signals...</span>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-slate-800 rounded-lg p-4 border border-yellow-700/50">
        <div className="flex items-center gap-2 text-yellow-400">
          <AlertTriangle className="h-5 w-5" />
          <div>
            <span className="font-medium">Unified AI Decision</span>
            <p className="text-sm text-slate-400 mt-1">
              {error === 'Failed to fetch unified recommendation'
                ? 'Server restart required. Please restart the API server to enable unified recommendations.'
                : error || 'Unable to load unified recommendation'}
            </p>
          </div>
        </div>
      </div>
    )
  }

  // Get recommendation styling
  const getRecommendationStyle = (rec: string) => {
    const upperRec = rec.toUpperCase()
    if (upperRec.includes('STRONG BUY')) {
      return {
        bg: 'from-green-600 to-green-700',
        border: 'border-green-500',
        icon: <TrendingUp className="h-6 w-6" />,
        textColor: 'text-white',
      }
    }
    if (upperRec.includes('BUY')) {
      return {
        bg: 'from-green-500 to-green-600',
        border: 'border-green-400',
        icon: <TrendingUp className="h-6 w-6" />,
        textColor: 'text-white',
      }
    }
    if (upperRec.includes('STRONG SELL')) {
      return {
        bg: 'from-red-600 to-red-700',
        border: 'border-red-500',
        icon: <TrendingDown className="h-6 w-6" />,
        textColor: 'text-white',
      }
    }
    if (upperRec.includes('SELL')) {
      return {
        bg: 'from-red-500 to-red-600',
        border: 'border-red-400',
        icon: <TrendingDown className="h-6 w-6" />,
        textColor: 'text-white',
      }
    }
    if (upperRec.includes('HOLD') || upperRec.includes('WAIT')) {
      return {
        bg: 'from-yellow-500 to-yellow-600',
        border: 'border-yellow-400',
        icon: <Minus className="h-6 w-6" />,
        textColor: 'text-black',
      }
    }
    return {
      bg: 'from-slate-600 to-slate-700',
      border: 'border-slate-500',
      icon: <Info className="h-6 w-6" />,
      textColor: 'text-white',
    }
  }

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'low': return 'text-green-400 bg-green-900/30'
      case 'medium': return 'text-yellow-400 bg-yellow-900/30'
      case 'high': return 'text-red-400 bg-red-900/30'
      default: return 'text-slate-400 bg-slate-700'
    }
  }

  const getSourceIcon = (source: string | undefined) => {
    if (!source) return '📋'
    // Normalize source name (handle both hyphens and underscores)
    const normalized = source.toLowerCase().replace(/-/g, '_')
    switch (normalized) {
      case 'triple_screen': return '📊'
      case 'multi_timeframe': return '⏱️'
      case 'technical': return '📈'
      case 'patterns': return '🔍'
      case 'ai_sentiment': return '🤖'
      default: return '📋'
    }
  }

  const getSourceName = (source: string | undefined) => {
    if (!source) return 'Unknown'
    // Normalize source name (handle both hyphens and underscores)
    const normalized = source.toLowerCase().replace(/-/g, '_')
    switch (normalized) {
      case 'triple_screen': return 'Triple Screen'
      case 'multi_timeframe': return 'Multi-Timeframe'
      case 'technical': return 'Technical'
      case 'patterns': return 'Pattern Recognition'
      case 'ai_sentiment': return 'AI Sentiment'
      default: return source
    }
  }

  const style = getRecommendationStyle(data.final_recommendation)

  return (
    <div className={`bg-gradient-to-r ${style.bg} rounded-lg border ${style.border} overflow-hidden shadow-lg`}>
      {/* Main Recommendation Banner */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full bg-white/20 ${style.textColor}`}>
              {style.icon}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Shield className={`h-4 w-4 ${style.textColor}`} />
                <span className={`text-xs font-medium uppercase tracking-wider ${style.textColor} opacity-80`}>
                  AI Unified Decision
                </span>
              </div>
              <h2 className={`text-2xl font-bold ${style.textColor}`}>
                {data.final_recommendation}
              </h2>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className={`text-xs ${style.textColor} opacity-80`}>Confidence</div>
              <div className={`text-2xl font-bold ${style.textColor}`}>{data.confidence}%</div>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className={`p-2 rounded-full bg-white/20 hover:bg-white/30 transition-colors ${style.textColor}`}
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Action Summary */}
        <p className={`mt-3 text-sm ${style.textColor} opacity-90`}>
          {data.action_summary}
        </p>

        {/* Quick Stats Row */}
        <div className="flex items-center gap-4 mt-4">
          <div className="flex items-center gap-2">
            <span className={`text-xs ${style.textColor} opacity-80`}>Score:</span>
            <span className={`text-sm font-semibold ${style.textColor}`}>{data.composite_score}/100</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs ${style.textColor} opacity-80`}>Risk:</span>
            <span className={`text-xs font-medium px-2 py-0.5 rounded ${getRiskColor(data.risk_level)}`}>
              {data.risk_level}
            </span>
          </div>
          {data.conflicts.length > 0 && (
            <div className="flex items-center gap-1">
              <AlertTriangle className={`h-4 w-4 ${style.textColor} opacity-80`} />
              <span className={`text-xs ${style.textColor} opacity-80`}>
                {data.conflicts.length} signal conflict{data.conflicts.length > 1 ? 's' : ''}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Expand/Collapse Button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2 bg-black/20 hover:bg-black/30 transition-colors flex items-center justify-center gap-2"
      >
        <span className={`text-xs font-medium ${style.textColor}`}>
          {expanded ? 'Hide Details' : 'Show Signal Breakdown'}
        </span>
        {expanded ? (
          <ChevronUp className={`h-4 w-4 ${style.textColor}`} />
        ) : (
          <ChevronDown className={`h-4 w-4 ${style.textColor}`} />
        )}
      </button>

      {/* Expanded Details */}
      {expanded && (
        <div className="bg-slate-900 p-4 space-y-4">
          {/* Sources Breakdown */}
          <div>
            <h3 className="text-sm font-medium text-slate-400 mb-3">Signal Sources (Weighted)</h3>
            <div className="space-y-2">
              {data.sources.map((source, index) => (
                <div key={index} className="bg-slate-800 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{getSourceIcon(source.source)}</span>
                      <span className="text-sm font-medium text-slate-200">
                        {getSourceName(source.source)}
                      </span>
                      <span className="text-xs text-slate-500">({(source.weight * 100).toFixed(0)}% weight)</span>
                    </div>
                    <span className={`text-sm font-semibold px-2 py-0.5 rounded ${
                      (source.signal || '').toUpperCase().includes('BUY') ? 'bg-green-900/50 text-green-400' :
                      (source.signal || '').toUpperCase().includes('SELL') ? 'bg-red-900/50 text-red-400' :
                      'bg-yellow-900/50 text-yellow-400'
                    }`}>
                      {source.signal || 'N/A'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          source.score >= 70 ? 'bg-green-500' :
                          source.score >= 50 ? 'bg-yellow-500' :
                          'bg-red-500'
                        }`}
                        style={{ width: `${source.score}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-400 w-12 text-right">
                      {source.score}/100
                    </span>
                  </div>
                  {source.details && (
                    <p className="text-xs text-slate-500 mt-2">{source.details}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Conflicts */}
          {data.conflicts.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-2">Detected Conflicts</h3>
              <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-3">
                <ul className="space-y-1">
                  {data.conflicts.map((conflict, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm text-red-300">
                      <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                      <span>{conflict}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* How it works */}
          <div className="pt-3 border-t border-slate-700">
            <div className="flex items-start gap-2 text-xs text-slate-500">
              <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <p>
                This unified recommendation aggregates signals from Triple Screen (30%), Multi-Timeframe Analysis (25%),
                Technical Indicators (20%), Pattern Recognition (15%), and AI Sentiment (10%). Conflicting signals
                reduce confidence.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
