import { useState, useEffect, useCallback } from 'react'
import { Activity, Zap, TrendingUp, Settings2, ChevronDown, ChevronUp, Info, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react'
import InsightModal from '../modals/InsightModal'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type TradingMode = 'scalp' | 'intraday' | 'swing'

interface IndicatorValue {
  value: number | null
  period?: number
  overbought?: number
  oversold?: number
  is_overbought?: boolean
  is_oversold?: boolean
}

interface MACDIndicator {
  macd_line: number | null
  signal_line: number | null
  histogram: number | null
  is_bullish: boolean
  is_bearish: boolean
  crossover: 'bullish' | 'bearish' | null
}

interface BollingerIndicator {
  upper: number | null
  middle: number | null
  lower: number | null
  price_position: string
}

interface ATRIndicator {
  value: number | null
  profit_target: number | null
  stop_loss: number | null
}

interface StochIndicator {
  k: number | null
  d: number | null
  is_overbought: boolean
  is_oversold: boolean
}

interface EMAIndicator {
  fast: number | null
  slow: number | null
  trend: 'bullish' | 'bearish'
}

interface WilliamsRIndicator {
  value: number | null
  period: number
  is_overbought: boolean
  is_oversold: boolean
}

interface ROCIndicator {
  value: number | null
  period: number
  is_positive: boolean
}

interface CCIIndicator {
  value: number | null
  period: number
  is_overbought: boolean
  is_oversold: boolean
}

interface ADXIndicator {
  value: number | null
  plus_di: number | null
  minus_di: number | null
  trend_strength: 'strong' | 'moderate' | 'weak'
}

interface MomentumIndicator {
  value: number | null
  period: number
  is_positive: boolean
}

interface OBVIndicator {
  value: number | null
  trend: 'rising' | 'falling' | 'flat'
}

interface VWAPIndicator {
  value: number | null
  price_vs_vwap: 'above' | 'below' | 'at'
}

interface Signals {
  buy_signals: string[]
  sell_signals: string[]
  neutral_signals: string[]
  overall: 'strong_buy' | 'buy' | 'neutral' | 'sell' | 'strong_sell'
  strength: number
  confidence: number
}

interface AdaptiveIndicators {
  mode: TradingMode
  auto_mode: boolean
  volatility: number
  config: Record<string, number>
  indicators: {
    rsi: IndicatorValue
    macd: MACDIndicator
    bollinger: BollingerIndicator
    atr: ATRIndicator
    stochastic: StochIndicator
    ema: EMAIndicator
    williams_r?: WilliamsRIndicator
    roc?: ROCIndicator
    cci?: CCIIndicator
    adx?: ADXIndicator
    momentum?: MomentumIndicator
    obv?: OBVIndicator
    vwap?: VWAPIndicator
  }
  signals: Signals
}

interface ModeRecommendation {
  recommended_mode: TradingMode
  current_mode: TradingMode
  volatility: number
  auto_mode: boolean
  reasoning: string[]
  config: Record<string, number>
}

interface AdaptiveIndicatorPanelProps {
  symbol: string
  onModeChange?: (mode: TradingMode) => void
  onInsightClick?: (indicator: string, data: unknown) => void
}

const MODE_ICONS = {
  scalp: Zap,
  intraday: Activity,
  swing: TrendingUp,
}

const MODE_COLORS = {
  scalp: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
  intraday: 'text-blue-400 bg-blue-400/10 border-blue-400/30',
  swing: 'text-purple-400 bg-purple-400/10 border-purple-400/30',
}

const MODE_DESCRIPTIONS = {
  scalp: 'Quick trades, tight stops, high volatility',
  intraday: 'Same-day positions, moderate risk',
  swing: 'Multi-day holds, wider stops, trending markets',
}

export default function AdaptiveIndicatorPanel({
  symbol,
  onModeChange,
  onInsightClick,
}: AdaptiveIndicatorPanelProps) {
  const [indicators, setIndicators] = useState<AdaptiveIndicators | null>(null)
  const [recommendation, setRecommendation] = useState<ModeRecommendation | null>(null)
  const [selectedMode, setSelectedMode] = useState<TradingMode>('intraday')
  const [autoMode, setAutoMode] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [showConfig, setShowConfig] = useState(false)
  const [showSignals, setShowSignals] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedIndicator, setSelectedIndicator] = useState<{ name: string; data: unknown } | null>(null)
  const [indicatorPage, setIndicatorPage] = useState(0) // 0 = primary, 1 = secondary indicators
  const [autoCycle, setAutoCycle] = useState(false)

  // Define indicator groups for cycling
  const indicatorGroups = [
    ['rsi', 'macd', 'stochastic', 'ema', 'bollinger', 'atr'], // Primary - always visible
    ['williams_r', 'cci', 'adx', 'roc', 'momentum', 'vwap'], // Secondary - cycle to view
  ]

  // Auto-cycle through indicator pages
  useEffect(() => {
    if (!autoCycle) return
    const interval = setInterval(() => {
      setIndicatorPage(prev => (prev + 1) % indicatorGroups.length)
    }, 8000) // Cycle every 8 seconds
    return () => clearInterval(interval)
  }, [autoCycle])

  const nextPage = useCallback(() => {
    setIndicatorPage(prev => (prev + 1) % indicatorGroups.length)
  }, [])

  const prevPage = useCallback(() => {
    setIndicatorPage(prev => (prev - 1 + indicatorGroups.length) % indicatorGroups.length)
  }, [])

  const handleIndicatorClick = (indicatorName: string, data: unknown) => {
    setSelectedIndicator({ name: indicatorName, data })
    setModalOpen(true)
    onInsightClick?.(indicatorName, data)
  }

  useEffect(() => {
    if (symbol) {
      fetchAdaptiveIndicators()
    }
  }, [symbol, selectedMode, autoMode])

  const fetchAdaptiveIndicators = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/analysis/adaptive/${symbol}?mode=${selectedMode}&auto_mode=${autoMode}`)
      if (response.ok) {
        const data = await response.json()
        setIndicators(data.indicators)
        setRecommendation(data.recommendation)

        if (autoMode && data.recommendation?.recommended_mode) {
          setSelectedMode(data.recommendation.recommended_mode)
          onModeChange?.(data.recommendation.recommended_mode)
        }
      }
    } catch (error) {
      console.error('Failed to fetch adaptive indicators:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleModeChange = (mode: TradingMode) => {
    setSelectedMode(mode)
    setAutoMode(false)
    onModeChange?.(mode)
  }

  const handleAutoModeToggle = () => {
    setAutoMode(!autoMode)
  }

  const getSignalColor = (signal: Signals['overall']) => {
    switch (signal) {
      case 'strong_buy':
        return 'text-green-400 bg-green-400/20'
      case 'buy':
        return 'text-green-400 bg-green-400/10'
      case 'strong_sell':
        return 'text-red-400 bg-red-400/20'
      case 'sell':
        return 'text-red-400 bg-red-400/10'
      default:
        return 'text-slate-400 bg-slate-400/10'
    }
  }

  const formatSignalLabel = (signal: Signals['overall']) => {
    return signal.replace('_', ' ').toUpperCase()
  }

  const ModeIcon = MODE_ICONS[selectedMode]

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-400" />
            <h3 className="font-semibold text-white">Adaptive Indicators</h3>
          </div>
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="p-1.5 rounded-lg hover:bg-slate-700 transition-colors"
          >
            <Settings2 className="h-4 w-4 text-slate-400" />
          </button>
        </div>

        {/* Mode Selector */}
        <div className="flex items-center gap-2 mb-3">
          {(['scalp', 'intraday', 'swing'] as TradingMode[]).map((mode) => {
            const Icon = MODE_ICONS[mode]
            const isSelected = selectedMode === mode
            return (
              <button
                key={mode}
                onClick={() => handleModeChange(mode)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  isSelected
                    ? MODE_COLORS[mode]
                    : 'text-slate-400 hover:bg-slate-700'
                } border ${isSelected ? '' : 'border-transparent'}`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="capitalize">{mode}</span>
              </button>
            )
          })}
        </div>

        {/* Auto Mode Toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={handleAutoModeToggle}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                autoMode ? 'bg-blue-500' : 'bg-slate-600'
              }`}
            >
              <span
                className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                  autoMode ? 'translate-x-4' : 'translate-x-1'
                }`}
              />
            </button>
            <span className="text-sm text-slate-400">Auto Mode</span>
          </div>
          {recommendation && autoMode && (
            <span className="text-xs text-slate-500">
              Volatility: {recommendation.volatility.toFixed(2)}%
            </span>
          )}
        </div>

        {/* Mode Description */}
        <p className="text-xs text-slate-500 mt-2">
          <ModeIcon className="h-3 w-3 inline mr-1" />
          {MODE_DESCRIPTIONS[selectedMode]}
        </p>
      </div>

      {/* Recommendation Reasoning */}
      {recommendation && recommendation.reasoning.length > 0 && (
        <div className="px-4 py-2 bg-slate-750 border-b border-slate-700">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-slate-400">
              {recommendation.reasoning.map((reason, i) => (
                <p key={i}>{reason}</p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Overall Signal */}
      {indicators?.signals && (
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-400">Overall Signal</span>
            <div
              className={`px-3 py-1 rounded-lg text-sm font-bold ${getSignalColor(
                indicators.signals.overall
              )}`}
            >
              {formatSignalLabel(indicators.signals.overall)}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                <span>Confidence</span>
                <span>{indicators.signals.confidence.toFixed(0)}%</span>
              </div>
              <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    indicators.signals.confidence >= 70
                      ? 'bg-green-400'
                      : indicators.signals.confidence >= 40
                      ? 'bg-yellow-400'
                      : 'bg-slate-500'
                  }`}
                  style={{ width: `${indicators.signals.confidence}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Indicators Grid with Cycling */}
      {indicators && (
        <div className="p-4">
          {/* Page Navigation Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">
                {indicatorPage === 0 ? 'Primary Indicators' : 'Secondary Indicators'}
              </span>
              <div className="flex items-center gap-1">
                {indicatorGroups.map((_, idx) => (
                  <div
                    key={idx}
                    className={`w-1.5 h-1.5 rounded-full transition-colors ${
                      idx === indicatorPage ? 'bg-blue-400' : 'bg-slate-600'
                    }`}
                  />
                ))}
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={prevPage}
                className="p-1 hover:bg-slate-700 rounded transition-colors"
                title="Previous indicators"
              >
                <ChevronLeft className="h-4 w-4 text-slate-400" />
              </button>
              <button
                onClick={() => setAutoCycle(!autoCycle)}
                className={`p-1 rounded transition-colors ${
                  autoCycle ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-slate-700 text-slate-400'
                }`}
                title={autoCycle ? 'Stop auto-cycling' : 'Start auto-cycling'}
              >
                <RotateCcw className={`h-4 w-4 ${autoCycle ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={nextPage}
                className="p-1 hover:bg-slate-700 rounded transition-colors"
                title="Next indicators"
              >
                <ChevronRight className="h-4 w-4 text-slate-400" />
              </button>
            </div>
          </div>

          {/* Primary Indicators (Page 0) */}
          {indicatorPage === 0 && (
            <div className="grid grid-cols-2 gap-3">
              {/* RSI */}
              <button
                onClick={() => handleIndicatorClick('RSI', indicators.indicators.rsi)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500">RSI ({indicators.indicators.rsi.period})</span>
                  {indicators.indicators.rsi.is_overbought && (
                    <span className="text-xs text-red-400">Overbought</span>
                  )}
                  {indicators.indicators.rsi.is_oversold && (
                    <span className="text-xs text-green-400">Oversold</span>
                  )}
                </div>
                <span
                  className={`text-lg font-bold ${
                    indicators.indicators.rsi.is_overbought
                      ? 'text-red-400'
                      : indicators.indicators.rsi.is_oversold
                      ? 'text-green-400'
                      : 'text-white'
                  }`}
                >
                  {indicators.indicators.rsi.value?.toFixed(1) || '-'}
                </span>
              </button>

              {/* MACD */}
              <button
                onClick={() => handleIndicatorClick('MACD', indicators.indicators.macd)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500">MACD</span>
                  {indicators.indicators.macd.crossover && (
                    <span
                      className={`text-xs ${
                        indicators.indicators.macd.crossover === 'bullish'
                          ? 'text-green-400'
                          : 'text-red-400'
                      }`}
                    >
                      {indicators.indicators.macd.crossover} X
                    </span>
                  )}
                </div>
                <span
                  className={`text-lg font-bold ${
                    indicators.indicators.macd.is_bullish ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {indicators.indicators.macd.histogram?.toFixed(3) || '-'}
                </span>
              </button>

              {/* Stochastic */}
              <button
                onClick={() => handleIndicatorClick('Stochastic', indicators.indicators.stochastic)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500">Stochastic</span>
                  {indicators.indicators.stochastic.is_overbought && (
                    <span className="text-xs text-red-400">OB</span>
                  )}
                  {indicators.indicators.stochastic.is_oversold && (
                    <span className="text-xs text-green-400">OS</span>
                  )}
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-lg font-bold text-white">
                    {indicators.indicators.stochastic.k?.toFixed(1) || '-'}
                  </span>
                  <span className="text-sm text-slate-400">
                    / {indicators.indicators.stochastic.d?.toFixed(1) || '-'}
                  </span>
                </div>
              </button>

              {/* EMA Trend */}
              <button
                onClick={() => handleIndicatorClick('EMA', indicators.indicators.ema)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="text-xs text-slate-500 mb-1">EMA Trend</div>
                <span
                  className={`text-lg font-bold capitalize ${
                    indicators.indicators.ema.trend === 'bullish' ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {indicators.indicators.ema.trend}
                </span>
              </button>

              {/* Bollinger Position */}
              <button
                onClick={() => handleIndicatorClick('Bollinger', indicators.indicators.bollinger)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="text-xs text-slate-500 mb-1">BB Position</div>
                <span className="text-lg font-bold text-white capitalize">
                  {indicators.indicators.bollinger.price_position.replace('_', ' ')}
                </span>
              </button>

              {/* ATR */}
              <button
                onClick={() => handleIndicatorClick('ATR', indicators.indicators.atr)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="text-xs text-slate-500 mb-1">ATR</div>
                <span className="text-lg font-bold text-white">
                  ${indicators.indicators.atr.value?.toFixed(2) || '-'}
                </span>
                <div className="flex items-center gap-2 mt-1 text-xs">
                  <span className="text-green-400">
                    TP: ${indicators.indicators.atr.profit_target?.toFixed(2) || '-'}
                  </span>
                  <span className="text-red-400">
                    SL: ${indicators.indicators.atr.stop_loss?.toFixed(2) || '-'}
                  </span>
                </div>
              </button>
            </div>
          )}

          {/* Secondary Indicators (Page 1) */}
          {indicatorPage === 1 && (
            <div className="grid grid-cols-2 gap-3">
              {/* Williams %R */}
              <button
                onClick={() => handleIndicatorClick('Williams %R', indicators.indicators.williams_r)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500">Williams %R</span>
                  {indicators.indicators.williams_r?.is_overbought && (
                    <span className="text-xs text-red-400">OB</span>
                  )}
                  {indicators.indicators.williams_r?.is_oversold && (
                    <span className="text-xs text-green-400">OS</span>
                  )}
                </div>
                <span
                  className={`text-lg font-bold ${
                    indicators.indicators.williams_r?.is_overbought
                      ? 'text-red-400'
                      : indicators.indicators.williams_r?.is_oversold
                      ? 'text-green-400'
                      : 'text-white'
                  }`}
                >
                  {indicators.indicators.williams_r?.value?.toFixed(1) || '-'}
                </span>
              </button>

              {/* CCI */}
              <button
                onClick={() => handleIndicatorClick('CCI', indicators.indicators.cci)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500">CCI (20)</span>
                  {indicators.indicators.cci?.is_overbought && (
                    <span className="text-xs text-red-400">OB</span>
                  )}
                  {indicators.indicators.cci?.is_oversold && (
                    <span className="text-xs text-green-400">OS</span>
                  )}
                </div>
                <span
                  className={`text-lg font-bold ${
                    indicators.indicators.cci?.is_overbought
                      ? 'text-red-400'
                      : indicators.indicators.cci?.is_oversold
                      ? 'text-green-400'
                      : 'text-white'
                  }`}
                >
                  {indicators.indicators.cci?.value?.toFixed(1) || '-'}
                </span>
              </button>

              {/* ADX */}
              <button
                onClick={() => handleIndicatorClick('ADX', indicators.indicators.adx)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500">ADX</span>
                  <span
                    className={`text-xs ${
                      indicators.indicators.adx?.trend_strength === 'strong'
                        ? 'text-green-400'
                        : indicators.indicators.adx?.trend_strength === 'weak'
                        ? 'text-red-400'
                        : 'text-yellow-400'
                    }`}
                  >
                    {indicators.indicators.adx?.trend_strength}
                  </span>
                </div>
                <span className="text-lg font-bold text-white">
                  {indicators.indicators.adx?.value?.toFixed(1) || '-'}
                </span>
                <div className="flex items-center gap-2 mt-1 text-xs">
                  <span className="text-green-400">
                    +DI: {indicators.indicators.adx?.plus_di?.toFixed(1) || '-'}
                  </span>
                  <span className="text-red-400">
                    -DI: {indicators.indicators.adx?.minus_di?.toFixed(1) || '-'}
                  </span>
                </div>
              </button>

              {/* ROC */}
              <button
                onClick={() => handleIndicatorClick('ROC', indicators.indicators.roc)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="text-xs text-slate-500 mb-1">ROC (12)</div>
                <span
                  className={`text-lg font-bold ${
                    indicators.indicators.roc?.is_positive ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {indicators.indicators.roc?.value?.toFixed(2) || '-'}%
                </span>
              </button>

              {/* Momentum */}
              <button
                onClick={() => handleIndicatorClick('Momentum', indicators.indicators.momentum)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="text-xs text-slate-500 mb-1">Momentum (10)</div>
                <span
                  className={`text-lg font-bold ${
                    indicators.indicators.momentum?.is_positive ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {indicators.indicators.momentum?.value?.toFixed(2) || '-'}
                </span>
              </button>

              {/* VWAP */}
              <button
                onClick={() => handleIndicatorClick('VWAP', indicators.indicators.vwap)}
                className="p-3 bg-slate-750 rounded-lg hover:bg-slate-700 transition-colors text-left"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500">VWAP</span>
                  <span
                    className={`text-xs ${
                      indicators.indicators.vwap?.price_vs_vwap === 'above'
                        ? 'text-green-400'
                        : indicators.indicators.vwap?.price_vs_vwap === 'below'
                        ? 'text-red-400'
                        : 'text-slate-400'
                    }`}
                  >
                    Price {indicators.indicators.vwap?.price_vs_vwap}
                  </span>
                </div>
                <span className="text-lg font-bold text-white">
                  ${indicators.indicators.vwap?.value?.toFixed(2) || '-'}
                </span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Signal Details */}
      {indicators?.signals && (
        <div className="border-t border-slate-700">
          <button
            onClick={() => setShowSignals(!showSignals)}
            className="w-full p-3 flex items-center justify-between text-sm text-slate-400 hover:bg-slate-750 transition-colors"
          >
            <span>Signal Details</span>
            {showSignals ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>

          {showSignals && (
            <div className="px-4 pb-4 space-y-2">
              {indicators.signals.buy_signals.length > 0 && (
                <div>
                  <div className="text-xs text-green-400 mb-1">Buy Signals</div>
                  {indicators.signals.buy_signals.map((signal, i) => (
                    <div key={i} className="text-xs text-slate-300 pl-2 border-l border-green-400/30">
                      {signal}
                    </div>
                  ))}
                </div>
              )}
              {indicators.signals.sell_signals.length > 0 && (
                <div>
                  <div className="text-xs text-red-400 mb-1">Sell Signals</div>
                  {indicators.signals.sell_signals.map((signal, i) => (
                    <div key={i} className="text-xs text-slate-300 pl-2 border-l border-red-400/30">
                      {signal}
                    </div>
                  ))}
                </div>
              )}
              {indicators.signals.neutral_signals.length > 0 && (
                <div>
                  <div className="text-xs text-slate-500 mb-1">Neutral</div>
                  {indicators.signals.neutral_signals.map((signal, i) => (
                    <div key={i} className="text-xs text-slate-400 pl-2 border-l border-slate-600">
                      {signal}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Config Panel */}
      {showConfig && indicators?.config && (
        <div className="border-t border-slate-700 p-4">
          <h4 className="text-sm font-medium text-slate-300 mb-3">
            {selectedMode.charAt(0).toUpperCase() + selectedMode.slice(1)} Mode Config
          </h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>RSI Period:</span>
              <span className="text-white">{indicators.config.rsi_period}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>MACD Fast:</span>
              <span className="text-white">{indicators.config.macd_fast}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>MACD Slow:</span>
              <span className="text-white">{indicators.config.macd_slow}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>BB Period:</span>
              <span className="text-white">{indicators.config.bb_period}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>ATR Period:</span>
              <span className="text-white">{indicators.config.atr_period}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Max Hold:</span>
              <span className="text-white">{indicators.config.hold_time_max_minutes}m</span>
            </div>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-slate-900/50 flex items-center justify-center">
          <div className="animate-spin h-6 w-6 border-2 border-blue-400 border-t-transparent rounded-full" />
        </div>
      )}

      {/* Insight Modal */}
      <InsightModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        indicator={selectedIndicator?.name || ''}
        data={selectedIndicator?.data as Record<string, unknown> || {}}
        symbol={symbol}
      />
    </div>
  )
}
