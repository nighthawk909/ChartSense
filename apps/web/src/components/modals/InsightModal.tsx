import { useState } from 'react'
import { X, Info, TrendingUp, TrendingDown, Minus, Calculator, BarChart2, Settings2 } from 'lucide-react'

interface InsightModalProps {
  isOpen: boolean
  onClose: () => void
  indicator: string
  data: Record<string, unknown>
  symbol?: string
}

interface FormulaStep {
  label: string
  value: string | number
  description?: string
}

const INDICATOR_INFO: Record<string, {
  name: string
  description: string
  formula: string
  interpretation: string[]
  parameters: { name: string; defaultValue: number | string; description: string }[]
}> = {
  RSI: {
    name: 'Relative Strength Index',
    description: 'RSI measures the magnitude of recent price changes to evaluate overbought or oversold conditions.',
    formula: 'RSI = 100 - (100 / (1 + RS)), where RS = Average Gain / Average Loss',
    interpretation: [
      'RSI > 70: Potentially overbought - price may be due for a pullback',
      'RSI < 30: Potentially oversold - price may be due for a bounce',
      'RSI 40-60: Neutral zone - no strong directional signal',
      'Divergence: When RSI and price move in opposite directions, trend reversal may be imminent',
    ],
    parameters: [
      { name: 'Period', defaultValue: 14, description: 'Number of periods for calculation (shorter = more sensitive)' },
      { name: 'Overbought', defaultValue: 70, description: 'Level above which asset is considered overbought' },
      { name: 'Oversold', defaultValue: 30, description: 'Level below which asset is considered oversold' },
    ],
  },
  MACD: {
    name: 'Moving Average Convergence Divergence',
    description: 'MACD shows the relationship between two EMAs and is used to spot changes in momentum, direction, and trend strength.',
    formula: 'MACD Line = EMA(12) - EMA(26), Signal Line = EMA(9) of MACD Line, Histogram = MACD - Signal',
    interpretation: [
      'MACD crosses above Signal: Bullish crossover - potential buy signal',
      'MACD crosses below Signal: Bearish crossover - potential sell signal',
      'Histogram expanding: Momentum increasing in trend direction',
      'Histogram contracting: Momentum weakening - potential reversal',
      'Zero line crossover: Trend direction change',
    ],
    parameters: [
      { name: 'Fast Period', defaultValue: 12, description: 'Fast EMA period' },
      { name: 'Slow Period', defaultValue: 26, description: 'Slow EMA period' },
      { name: 'Signal Period', defaultValue: 9, description: 'Signal line smoothing period' },
    ],
  },
  Stochastic: {
    name: 'Stochastic Oscillator',
    description: 'Compares closing price to the price range over a given period to identify overbought/oversold conditions.',
    formula: '%K = ((Close - Lowest Low) / (Highest High - Lowest Low)) x 100, %D = SMA(%K)',
    interpretation: [
      '%K > 80: Overbought zone - potential selling pressure',
      '%K < 20: Oversold zone - potential buying opportunity',
      '%K crosses above %D: Bullish signal',
      '%K crosses below %D: Bearish signal',
      'Look for divergences between price and stochastic',
    ],
    parameters: [
      { name: 'K Period', defaultValue: 14, description: 'Lookback period for %K calculation' },
      { name: 'D Period', defaultValue: 3, description: 'Smoothing period for %D (signal line)' },
    ],
  },
  Bollinger: {
    name: 'Bollinger Bands',
    description: 'Bollinger Bands consist of a middle band (SMA) with upper and lower bands at standard deviation levels.',
    formula: 'Upper = SMA + (2 x StdDev), Middle = SMA(20), Lower = SMA - (2 x StdDev)',
    interpretation: [
      'Price at upper band: Potentially overbought, may face resistance',
      'Price at lower band: Potentially oversold, may find support',
      'Band squeeze (narrow): Low volatility, breakout expected',
      'Band expansion: High volatility, trend continuation',
      'Walking the band: Strong trend when price hugs upper/lower band',
    ],
    parameters: [
      { name: 'Period', defaultValue: 20, description: 'Moving average period' },
      { name: 'Std Dev', defaultValue: 2, description: 'Standard deviation multiplier for bands' },
    ],
  },
  ATR: {
    name: 'Average True Range',
    description: 'ATR measures market volatility by analyzing the range of price movement.',
    formula: 'TR = max(High-Low, |High-PrevClose|, |Low-PrevClose|), ATR = EMA(TR, period)',
    interpretation: [
      'High ATR: Market is volatile - wider stops needed',
      'Low ATR: Market is calm - tighter stops possible',
      'Rising ATR: Volatility increasing - expect larger moves',
      'Falling ATR: Volatility decreasing - range-bound expected',
      'Use ATR multiples for stop-loss and take-profit levels',
    ],
    parameters: [
      { name: 'Period', defaultValue: 14, description: 'ATR calculation period' },
      { name: 'Stop Mult', defaultValue: 1.5, description: 'ATR multiplier for stop-loss' },
      { name: 'Target Mult', defaultValue: 2, description: 'ATR multiplier for profit target' },
    ],
  },
  EMA: {
    name: 'Exponential Moving Average',
    description: 'EMA gives more weight to recent prices, making it more responsive to new information.',
    formula: 'EMA = (Close x Multiplier) + (Previous EMA x (1 - Multiplier)), Multiplier = 2/(Period+1)',
    interpretation: [
      'Price above EMA: Bullish trend',
      'Price below EMA: Bearish trend',
      'Fast EMA crosses above Slow EMA: Golden cross - bullish',
      'Fast EMA crosses below Slow EMA: Death cross - bearish',
      'EMA slope indicates trend strength',
    ],
    parameters: [
      { name: 'Fast Period', defaultValue: 9, description: 'Fast EMA period' },
      { name: 'Slow Period', defaultValue: 21, description: 'Slow EMA period' },
    ],
  },
}

export default function InsightModal({ isOpen, onClose, indicator, data, symbol }: InsightModalProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'calculation' | 'settings'>('overview')

  if (!isOpen) return null

  const info = INDICATOR_INFO[indicator] || {
    name: indicator,
    description: 'Technical indicator',
    formula: 'N/A',
    interpretation: [],
    parameters: [],
  }

  const getSignalIcon = () => {
    if (!data) return <Minus className="h-5 w-5 text-slate-400" />

    // Check for bullish/bearish signals based on indicator type
    if (indicator === 'RSI') {
      const value = data.value as number
      if (value && value < 30) return <TrendingUp className="h-5 w-5 text-green-400" />
      if (value && value > 70) return <TrendingDown className="h-5 w-5 text-red-400" />
    }

    if (indicator === 'MACD') {
      if (data.is_bullish) return <TrendingUp className="h-5 w-5 text-green-400" />
      if (data.is_bearish) return <TrendingDown className="h-5 w-5 text-red-400" />
    }

    if (indicator === 'EMA') {
      if (data.trend === 'bullish') return <TrendingUp className="h-5 w-5 text-green-400" />
      if (data.trend === 'bearish') return <TrendingDown className="h-5 w-5 text-red-400" />
    }

    return <Minus className="h-5 w-5 text-slate-400" />
  }

  const getSignalText = () => {
    if (!data) return 'No data'

    if (indicator === 'RSI') {
      const value = data.value as number
      if (value !== undefined && value !== null) {
        if (value < 30) return 'Oversold - Potential Buy'
        if (value > 70) return 'Overbought - Potential Sell'
        if (value < 40) return 'Approaching Oversold'
        if (value > 60) return 'Approaching Overbought'
        return 'Neutral'
      }
    }

    if (indicator === 'MACD') {
      if (data.crossover === 'bullish') return 'Bullish Crossover'
      if (data.crossover === 'bearish') return 'Bearish Crossover'
      if (data.is_bullish) return 'Bullish Momentum'
      if (data.is_bearish) return 'Bearish Momentum'
    }

    if (indicator === 'Stochastic') {
      if (data.is_oversold) return 'Oversold - Potential Bounce'
      if (data.is_overbought) return 'Overbought - Potential Pullback'
      return 'Neutral'
    }

    if (indicator === 'EMA') {
      if (data.trend === 'bullish') return 'Bullish Trend'
      if (data.trend === 'bearish') return 'Bearish Trend'
    }

    if (indicator === 'Bollinger') {
      const position = data.price_position as string
      if (position === 'above_upper') return 'Overbought - At Upper Band'
      if (position === 'below_lower') return 'Oversold - At Lower Band'
      if (position === 'upper_half') return 'Upper Half of Bands'
      if (position === 'lower_half') return 'Lower Half of Bands'
    }

    return 'Neutral'
  }

  const renderDataValues = () => {
    if (!data) return null

    const entries = Object.entries(data).filter(([key]) =>
      !['is_bullish', 'is_bearish', 'is_overbought', 'is_oversold'].includes(key)
    )

    return (
      <div className="grid grid-cols-2 gap-3">
        {entries.map(([key, value]) => (
          <div key={key} className="bg-slate-750 rounded-lg p-3">
            <div className="text-xs text-slate-500 mb-1">
              {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </div>
            <div className="text-white font-medium">
              {typeof value === 'number'
                ? value.toFixed(value < 1 ? 4 : 2)
                : String(value)}
            </div>
          </div>
        ))}
      </div>
    )
  }

  const renderCalculationSteps = (): FormulaStep[] => {
    if (!data) return []

    if (indicator === 'RSI') {
      return [
        { label: 'Current RSI', value: (data.value as number)?.toFixed(2) || 'N/A', description: 'Final calculated RSI value' },
        { label: 'Period Used', value: data.period as number || 14, description: 'Number of periods in calculation' },
        { label: 'Overbought Level', value: data.overbought as number || 70, description: 'Threshold for overbought condition' },
        { label: 'Oversold Level', value: data.oversold as number || 30, description: 'Threshold for oversold condition' },
      ]
    }

    if (indicator === 'MACD') {
      return [
        { label: 'MACD Line', value: (data.macd_line as number)?.toFixed(4) || 'N/A', description: 'Fast EMA - Slow EMA' },
        { label: 'Signal Line', value: (data.signal_line as number)?.toFixed(4) || 'N/A', description: '9-period EMA of MACD' },
        { label: 'Histogram', value: (data.histogram as number)?.toFixed(4) || 'N/A', description: 'MACD - Signal' },
        { label: 'Crossover', value: (data.crossover as string) || 'None', description: 'Recent line crossing event' },
      ]
    }

    if (indicator === 'Stochastic') {
      return [
        { label: '%K Value', value: (data.k as number)?.toFixed(2) || 'N/A', description: 'Fast stochastic line' },
        { label: '%D Value', value: (data.d as number)?.toFixed(2) || 'N/A', description: 'Slow signal line' },
        { label: 'Overbought', value: data.is_overbought ? 'Yes' : 'No', description: 'Above 80 threshold' },
        { label: 'Oversold', value: data.is_oversold ? 'Yes' : 'No', description: 'Below 20 threshold' },
      ]
    }

    if (indicator === 'ATR') {
      return [
        { label: 'ATR Value', value: `$${(data.value as number)?.toFixed(2)}` || 'N/A', description: 'Average True Range' },
        { label: 'Profit Target', value: `$${(data.profit_target as number)?.toFixed(2)}` || 'N/A', description: 'Suggested profit distance' },
        { label: 'Stop Loss', value: `$${(data.stop_loss as number)?.toFixed(2)}` || 'N/A', description: 'Suggested stop distance' },
      ]
    }

    if (indicator === 'Bollinger') {
      return [
        { label: 'Upper Band', value: `$${(data.upper as number)?.toFixed(2)}` || 'N/A', description: 'SMA + 2 StdDev' },
        { label: 'Middle Band', value: `$${(data.middle as number)?.toFixed(2)}` || 'N/A', description: '20-period SMA' },
        { label: 'Lower Band', value: `$${(data.lower as number)?.toFixed(2)}` || 'N/A', description: 'SMA - 2 StdDev' },
        { label: 'Price Position', value: (data.price_position as string)?.replace('_', ' ') || 'N/A', description: 'Where price is relative to bands' },
      ]
    }

    if (indicator === 'EMA') {
      return [
        { label: 'Fast EMA', value: `$${(data.fast as number)?.toFixed(2)}` || 'N/A', description: 'Short-term EMA' },
        { label: 'Slow EMA', value: `$${(data.slow as number)?.toFixed(2)}` || 'N/A', description: 'Long-term EMA' },
        { label: 'Trend', value: (data.trend as string) || 'N/A', description: 'Current trend direction' },
      ]
    }

    return []
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-slate-800 rounded-xl border border-slate-700 w-full max-w-lg max-h-[90vh] overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <BarChart2 className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <h2 className="font-semibold text-white">{info.name}</h2>
              {symbol && <p className="text-sm text-slate-400">{symbol}</p>}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700 transition-colors"
          >
            <X className="h-5 w-5 text-slate-400" />
          </button>
        </div>

        {/* Signal Summary */}
        <div className="px-4 py-3 bg-slate-750 border-b border-slate-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {getSignalIcon()}
              <span className="font-medium text-white">{getSignalText()}</span>
            </div>
            {data && 'value' in data && typeof data.value === 'number' && (
              <span className="text-2xl font-bold text-white">
                {data.value.toFixed(data.value < 1 ? 4 : 2)}
              </span>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-700">
          <button
            onClick={() => setActiveTab('overview')}
            className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === 'overview'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Info className="h-4 w-4 inline mr-1.5" />
            Overview
          </button>
          <button
            onClick={() => setActiveTab('calculation')}
            className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === 'calculation'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Calculator className="h-4 w-4 inline mr-1.5" />
            Calculation
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === 'settings'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Settings2 className="h-4 w-4 inline mr-1.5" />
            Parameters
          </button>
        </div>

        {/* Content */}
        <div className="p-4 max-h-[400px] overflow-y-auto">
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-2">Description</h3>
                <p className="text-sm text-slate-400">{info.description}</p>
              </div>

              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-2">Formula</h3>
                <div className="bg-slate-750 rounded-lg p-3">
                  <code className="text-xs text-blue-400 font-mono">{info.formula}</code>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-2">How to Interpret</h3>
                <ul className="space-y-2">
                  {info.interpretation.map((item, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                      <span className="text-blue-400 mt-1">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'calculation' && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3">Current Values</h3>
                {renderDataValues()}
              </div>

              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3">Calculation Breakdown</h3>
                <div className="space-y-2">
                  {renderCalculationSteps().map((step, i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-750 rounded-lg p-3">
                      <div>
                        <div className="text-sm text-white">{step.label}</div>
                        {step.description && (
                          <div className="text-xs text-slate-500">{step.description}</div>
                        )}
                      </div>
                      <div className="text-sm font-mono text-blue-400">{step.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3">Indicator Parameters</h3>
                <div className="space-y-3">
                  {info.parameters.map((param, i) => (
                    <div key={i} className="bg-slate-750 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-white">{param.name}</span>
                        <span className="text-sm text-blue-400 font-mono">{param.defaultValue}</span>
                      </div>
                      <p className="text-xs text-slate-500">{param.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="text-xs text-slate-500 mt-4">
                <Info className="h-3 w-3 inline mr-1" />
                Parameters are automatically adjusted based on the selected trading mode (Scalp/Intraday/Swing)
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700 bg-slate-750">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Click indicators on the chart to see detailed breakdown</span>
            <button
              onClick={onClose}
              className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
