import { useState, useEffect } from 'react'
import { Save, RefreshCw, AlertCircle, CheckCircle, Shield, TrendingUp, Clock, Zap, DollarSign, Target, Activity, Bitcoin } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface BotSettings {
  // Risk Management
  risk_per_trade: number
  max_position_size: number
  default_stop_loss_pct: number
  default_take_profit_pct: number

  // Exit Strategies
  trailing_stop_enabled: boolean
  trailing_stop_pct: number
  partial_profit_enabled: boolean
  partial_profit_pct: number
  partial_profit_at: number

  // Entry Criteria
  min_volume: number
  entry_score_threshold: number
  enabled_symbols: string[]

  // Trading Mode
  paper_trading: boolean
  auto_optimize: boolean
  reinvest_profits: boolean
  compounding_enabled: boolean

  // Intraday Settings
  intraday_enabled: boolean
  intraday_timeframe: string
  max_trades_per_day: number

  // Auto Trade (AI Control)
  auto_trade_mode: boolean
  ai_risk_tolerance: string

  // Broker
  broker: string

  // Crypto Trading
  crypto_trading_enabled: boolean
  crypto_symbols: string[]
  crypto_max_positions: number
}

const DEFAULT_SETTINGS: BotSettings = {
  risk_per_trade: 0.01,
  max_position_size: 5000,
  default_stop_loss_pct: 0.05,
  default_take_profit_pct: 0.10,
  trailing_stop_enabled: false,
  trailing_stop_pct: 0.03,
  partial_profit_enabled: false,
  partial_profit_pct: 0.5,
  partial_profit_at: 0.05,
  min_volume: 1000000,
  entry_score_threshold: 70,
  enabled_symbols: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'],
  paper_trading: true,
  auto_optimize: false,
  reinvest_profits: true,
  compounding_enabled: true,
  intraday_enabled: false,
  intraday_timeframe: '5min',
  max_trades_per_day: 10,
  auto_trade_mode: false,
  ai_risk_tolerance: 'moderate',
  broker: 'alpaca',
  crypto_trading_enabled: false,
  crypto_symbols: ['BTC/USD', 'ETH/USD'],
  crypto_max_positions: 2,
}

export default function Settings() {
  const [settings, setSettings] = useState<BotSettings>(DEFAULT_SETTINGS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [activeTab, setActiveTab] = useState<'risk' | 'exit' | 'trading' | 'intraday' | 'crypto' | 'broker'>('risk')

  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API_URL}/api/settings/`)
      if (response.ok) {
        const data = await response.json()
        const serverSettings = data.settings || data
        setSettings({ ...DEFAULT_SETTINGS, ...serverSettings })
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error)
      setMessage({ type: 'error', text: 'Failed to load settings' })
    } finally {
      setLoading(false)
    }
  }

  const saveSettings = async () => {
    setSaving(true)
    setMessage(null)

    try {
      // Map frontend field names to API field names
      const apiSettings = {
        settings: {
          enabled_symbols: settings.enabled_symbols,
          max_positions: 5,
          max_position_size_pct: settings.max_position_size / 100000, // Convert to percentage
          risk_per_trade_pct: settings.risk_per_trade,
          max_daily_loss_pct: 0.03,
          default_stop_loss_pct: settings.default_stop_loss_pct,
          default_take_profit_pct: settings.default_take_profit_pct,
          trailing_stop_enabled: settings.trailing_stop_enabled,
          trailing_stop_pct: settings.trailing_stop_pct,
          trailing_stop_activation_pct: 0.05,
          partial_profit_enabled: settings.partial_profit_enabled,
          partial_profit_pct: settings.partial_profit_pct,
          partial_profit_at: settings.partial_profit_at,
          entry_score_threshold: settings.entry_score_threshold,
          swing_profit_target_pct: 0.08,
          longterm_profit_target_pct: 0.15,
          paper_trading: settings.paper_trading,
          trading_hours_only: true,
          auto_optimize: settings.auto_optimize,
          reinvest_profits: settings.reinvest_profits,
          compounding_enabled: settings.compounding_enabled,
          intraday_enabled: settings.intraday_enabled,
          intraday_timeframe: settings.intraday_timeframe,
          max_trades_per_day: settings.max_trades_per_day,
          auto_trade_mode: settings.auto_trade_mode,
          ai_risk_tolerance: settings.ai_risk_tolerance,
          broker: settings.broker,
          crypto_trading_enabled: settings.crypto_trading_enabled,
          crypto_symbols: settings.crypto_symbols,
          crypto_max_positions: settings.crypto_max_positions,
        }
      }

      const response = await fetch(`${API_URL}/api/settings/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(apiSettings),
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Settings saved successfully!' })
      } else {
        setMessage({ type: 'error', text: 'Failed to save settings' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save settings' })
    } finally {
      setSaving(false)
    }
  }

  const resetToDefaults = async () => {
    try {
      const response = await fetch(`${API_URL}/api/settings/reset`, { method: 'POST' })
      if (response.ok) {
        setSettings(DEFAULT_SETTINGS)
        setMessage({ type: 'success', text: 'Settings reset to defaults' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to reset settings' })
    }
  }

  useEffect(() => {
    fetchSettings()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    )
  }

  const tabs = [
    { id: 'risk', label: 'Risk Management', icon: Shield },
    { id: 'exit', label: 'Exit Strategies', icon: Target },
    { id: 'trading', label: 'Trading Mode', icon: Activity },
    { id: 'intraday', label: 'Intraday', icon: Clock },
    { id: 'crypto', label: 'Crypto', icon: Bitcoin },
    { id: 'broker', label: 'Broker', icon: DollarSign },
  ]

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Bot Settings</h1>
        <div className="flex gap-3">
          <button
            onClick={resetToDefaults}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
          >
            Reset to Defaults
          </button>
          <button
            onClick={saveSettings}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors flex items-center gap-2"
          >
            {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save Changes
          </button>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${
          message.type === 'success' ? 'bg-green-900/50 border border-green-700' : 'bg-red-900/50 border border-red-700'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle className="h-5 w-5 text-green-500" />
          ) : (
            <AlertCircle className="h-5 w-5 text-red-500" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* Trading Mode Banner */}
      <div className={`p-4 rounded-lg flex items-center justify-between ${
        settings.paper_trading ? 'bg-yellow-900/30 border border-yellow-700/50' : 'bg-green-900/30 border border-green-700/50'
      }`}>
        <div className="flex items-center gap-3">
          {settings.paper_trading ? (
            <Shield className="h-6 w-6 text-yellow-500" />
          ) : (
            <DollarSign className="h-6 w-6 text-green-500" />
          )}
          <div>
            <p className="font-semibold">{settings.paper_trading ? 'Paper Trading Mode' : 'LIVE Trading Mode'}</p>
            <p className="text-sm text-slate-400">
              {settings.paper_trading ? 'Trading with simulated money - no real risk' : 'Trading with real money - be careful!'}
            </p>
          </div>
        </div>
        <button
          onClick={() => setSettings({ ...settings, paper_trading: !settings.paper_trading })}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            settings.paper_trading
              ? 'bg-green-600 hover:bg-green-500 text-white'
              : 'bg-yellow-600 hover:bg-yellow-500 text-white'
          }`}
        >
          Switch to {settings.paper_trading ? 'Live' : 'Paper'} Trading
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-700 pb-2">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Risk Management Tab */}
      {activeTab === 'risk' && (
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-500" />
              Position Sizing
            </h2>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Risk Per Trade (%)</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="0.5"
                    max="5"
                    step="0.5"
                    value={settings.risk_per_trade * 100}
                    onChange={(e) => setSettings({ ...settings, risk_per_trade: parseFloat(e.target.value) / 100 })}
                    className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                  <span className="text-lg font-semibold w-16 text-right">{(settings.risk_per_trade * 100).toFixed(1)}%</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">Maximum % of portfolio to risk per trade</p>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">Max Position Size ($)</label>
                <input
                  type="number"
                  value={settings.max_position_size}
                  onChange={(e) => setSettings({ ...settings, max_position_size: parseFloat(e.target.value) })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
                <p className="text-xs text-slate-500 mt-1">Maximum dollar amount per position</p>
              </div>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-500" />
              Profit Reinvestment
            </h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Reinvest Profits</p>
                  <p className="text-sm text-slate-400">Automatically reinvest trading profits</p>
                </div>
                <Toggle
                  checked={settings.reinvest_profits}
                  onChange={(checked) => setSettings({ ...settings, reinvest_profits: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Enable Compounding</p>
                  <p className="text-sm text-slate-400">Increase position sizes as portfolio grows</p>
                </div>
                <Toggle
                  checked={settings.compounding_enabled}
                  onChange={(checked) => setSettings({ ...settings, compounding_enabled: checked })}
                />
              </div>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Entry Criteria</h2>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Min Volume</label>
                <input
                  type="number"
                  value={settings.min_volume}
                  onChange={(e) => setSettings({ ...settings, min_volume: parseInt(e.target.value) })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">Entry Score Threshold (0-100)</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={settings.entry_score_threshold}
                    onChange={(e) => setSettings({ ...settings, entry_score_threshold: parseInt(e.target.value) })}
                    className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                  <span className="text-lg font-semibold w-12 text-right">{settings.entry_score_threshold}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Trading Symbols</h2>
            <input
              type="text"
              value={settings.enabled_symbols?.join(', ') || ''}
              onChange={(e) => setSettings({
                ...settings,
                enabled_symbols: e.target.value.split(',').map(s => s.trim().toUpperCase()).filter(s => s)
              })}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              placeholder="AAPL, MSFT, GOOGL, AMZN, NVDA"
            />
            <p className="text-xs text-slate-500 mt-2">Enter symbols separated by commas</p>
          </div>
        </div>
      )}

      {/* Exit Strategies Tab */}
      {activeTab === 'exit' && (
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Target className="h-5 w-5 text-red-500" />
              Stop Loss Settings
            </h2>
            <div className="space-y-6">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Default Stop Loss (%)</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="1"
                    max="20"
                    step="0.5"
                    value={settings.default_stop_loss_pct * 100}
                    onChange={(e) => setSettings({ ...settings, default_stop_loss_pct: parseFloat(e.target.value) / 100 })}
                    className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-red-500"
                  />
                  <span className="text-lg font-semibold w-16 text-right text-red-400">{(settings.default_stop_loss_pct * 100).toFixed(1)}%</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">Sell when price drops this much below entry</p>
              </div>

              <div className="border-t border-slate-700 pt-4">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="font-medium">Trailing Stop Loss</p>
                    <p className="text-sm text-slate-400">Stop loss follows price upward to lock in profits</p>
                  </div>
                  <Toggle
                    checked={settings.trailing_stop_enabled}
                    onChange={(checked) => setSettings({ ...settings, trailing_stop_enabled: checked })}
                  />
                </div>
                {settings.trailing_stop_enabled && (
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Trailing Distance (%)</label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="1"
                        max="10"
                        step="0.5"
                        value={settings.trailing_stop_pct * 100}
                        onChange={(e) => setSettings({ ...settings, trailing_stop_pct: parseFloat(e.target.value) / 100 })}
                        className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
                      />
                      <span className="text-lg font-semibold w-16 text-right text-orange-400">{(settings.trailing_stop_pct * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-500" />
              Take Profit Settings
            </h2>
            <div className="space-y-6">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Default Take Profit (%)</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="2"
                    max="50"
                    step="1"
                    value={settings.default_take_profit_pct * 100}
                    onChange={(e) => setSettings({ ...settings, default_take_profit_pct: parseFloat(e.target.value) / 100 })}
                    className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-green-500"
                  />
                  <span className="text-lg font-semibold w-16 text-right text-green-400">{(settings.default_take_profit_pct * 100).toFixed(0)}%</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">Sell when price rises this much above entry</p>
              </div>

              <div className="border-t border-slate-700 pt-4">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="font-medium">Partial Profit Taking</p>
                    <p className="text-sm text-slate-400">Sell a portion of position at intermediate target</p>
                  </div>
                  <Toggle
                    checked={settings.partial_profit_enabled}
                    onChange={(checked) => setSettings({ ...settings, partial_profit_enabled: checked })}
                  />
                </div>
                {settings.partial_profit_enabled && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Take Profit At (%)</label>
                      <div className="flex items-center gap-4">
                        <input
                          type="range"
                          min="2"
                          max="20"
                          step="1"
                          value={settings.partial_profit_at * 100}
                          onChange={(e) => setSettings({ ...settings, partial_profit_at: parseFloat(e.target.value) / 100 })}
                          className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-green-500"
                        />
                        <span className="text-lg font-semibold w-12 text-right">{(settings.partial_profit_at * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Portion to Sell (%)</label>
                      <div className="flex items-center gap-4">
                        <input
                          type="range"
                          min="10"
                          max="90"
                          step="10"
                          value={settings.partial_profit_pct * 100}
                          onChange={(e) => setSettings({ ...settings, partial_profit_pct: parseFloat(e.target.value) / 100 })}
                          className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        />
                        <span className="text-lg font-semibold w-12 text-right">{(settings.partial_profit_pct * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Visual Example */}
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Exit Strategy Preview</h2>
            <div className="relative h-32 bg-slate-900 rounded-lg p-4">
              <div className="absolute left-4 right-4 top-1/2 h-0.5 bg-slate-600"></div>
              <div className="absolute left-4 top-1/2 -translate-y-1/2 w-3 h-3 bg-blue-500 rounded-full"></div>
              <p className="absolute left-4 bottom-2 text-xs text-slate-400">Entry</p>

              <div
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-red-500 rounded-full"
                style={{ left: `${20 + (1 - settings.default_stop_loss_pct) * 30}%` }}
              ></div>
              <p className="absolute bottom-2 text-xs text-red-400" style={{ left: `${20 + (1 - settings.default_stop_loss_pct) * 30}%` }}>
                Stop: -{(settings.default_stop_loss_pct * 100).toFixed(0)}%
              </p>

              {settings.partial_profit_enabled && (
                <>
                  <div
                    className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-yellow-500 rounded-full"
                    style={{ left: `${20 + settings.partial_profit_at * 200}%` }}
                  ></div>
                  <p className="absolute top-2 text-xs text-yellow-400" style={{ left: `${20 + settings.partial_profit_at * 200}%` }}>
                    Partial: +{(settings.partial_profit_at * 100).toFixed(0)}%
                  </p>
                </>
              )}

              <div
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-green-500 rounded-full"
                style={{ left: `${Math.min(85, 20 + settings.default_take_profit_pct * 200)}%` }}
              ></div>
              <p className="absolute bottom-2 text-xs text-green-400" style={{ left: `${Math.min(85, 20 + settings.default_take_profit_pct * 200)}%` }}>
                Target: +{(settings.default_take_profit_pct * 100).toFixed(0)}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Trading Mode Tab */}
      {activeTab === 'trading' && (
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Zap className="h-5 w-5 text-purple-500" />
              Auto Trade Mode (AI Controlled)
            </h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Enable Auto Trade</p>
                  <p className="text-sm text-slate-400">Let AI automatically manage buy/sell decisions and parameters</p>
                </div>
                <Toggle
                  checked={settings.auto_trade_mode}
                  onChange={(checked) => setSettings({ ...settings, auto_trade_mode: checked })}
                />
              </div>

              {settings.auto_trade_mode && (
                <div className="mt-4 p-4 bg-slate-700/50 rounded-lg">
                  <label className="block text-sm text-slate-400 mb-3">AI Risk Tolerance</label>
                  <div className="grid grid-cols-3 gap-3">
                    {['conservative', 'moderate', 'aggressive'].map((level) => (
                      <button
                        key={level}
                        onClick={() => setSettings({ ...settings, ai_risk_tolerance: level })}
                        className={`px-4 py-3 rounded-lg capitalize transition-colors ${
                          settings.ai_risk_tolerance === level
                            ? level === 'conservative' ? 'bg-blue-600 text-white'
                              : level === 'moderate' ? 'bg-yellow-600 text-white'
                              : 'bg-red-600 text-white'
                            : 'bg-slate-700 hover:bg-slate-600'
                        }`}
                      >
                        {level}
                      </button>
                    ))}
                  </div>
                  <p className="text-xs text-slate-500 mt-3">
                    {settings.ai_risk_tolerance === 'conservative' && 'Lower risk, smaller positions, tighter stop losses'}
                    {settings.ai_risk_tolerance === 'moderate' && 'Balanced approach with medium-sized positions'}
                    {settings.ai_risk_tolerance === 'aggressive' && 'Higher risk tolerance, larger positions, wider stops'}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Auto Optimization</h2>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Enable Auto Optimize</p>
                <p className="text-sm text-slate-400">Automatically adjust parameters based on performance</p>
              </div>
              <Toggle
                checked={settings.auto_optimize}
                onChange={(checked) => setSettings({ ...settings, auto_optimize: checked })}
              />
            </div>
          </div>
        </div>
      )}

      {/* Intraday Tab */}
      {activeTab === 'intraday' && (
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Clock className="h-5 w-5 text-cyan-500" />
              Intraday Trading
            </h2>
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Enable Intraday Trading</p>
                  <p className="text-sm text-slate-400">Allow trades within the same day using shorter timeframes</p>
                </div>
                <Toggle
                  checked={settings.intraday_enabled}
                  onChange={(checked) => setSettings({ ...settings, intraday_enabled: checked })}
                />
              </div>

              {settings.intraday_enabled && (
                <>
                  <div>
                    <label className="block text-sm text-slate-400 mb-3">Timeframe</label>
                    <div className="grid grid-cols-5 gap-2">
                      {['1min', '5min', '15min', '30min', '1hour'].map((tf) => (
                        <button
                          key={tf}
                          onClick={() => setSettings({ ...settings, intraday_timeframe: tf })}
                          className={`px-3 py-2 rounded-lg transition-colors ${
                            settings.intraday_timeframe === tf
                              ? 'bg-cyan-600 text-white'
                              : 'bg-slate-700 hover:bg-slate-600'
                          }`}
                        >
                          {tf}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Max Trades Per Day</label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="1"
                        max="50"
                        value={settings.max_trades_per_day}
                        onChange={(e) => setSettings({ ...settings, max_trades_per_day: parseInt(e.target.value) })}
                        className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                      />
                      <span className="text-lg font-semibold w-12 text-right">{settings.max_trades_per_day}</span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {!settings.intraday_enabled && (
            <div className="bg-blue-900/30 border border-blue-700/50 rounded-lg p-4">
              <p className="text-sm text-blue-300">
                <strong>Note:</strong> Intraday trading requires more active monitoring and may incur higher fees.
                The bot currently focuses on swing trading (daily timeframe) for more reliable signals.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Crypto Tab */}
      {activeTab === 'crypto' && (
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Bitcoin className="h-5 w-5 text-orange-500" />
              Crypto Trading
            </h2>
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Enable Crypto Trading</p>
                  <p className="text-sm text-slate-400">Trade cryptocurrencies 24/7 via Alpaca</p>
                </div>
                <Toggle
                  checked={settings.crypto_trading_enabled}
                  onChange={(checked) => setSettings({ ...settings, crypto_trading_enabled: checked })}
                />
              </div>

              {settings.crypto_trading_enabled && (
                <>
                  <div>
                    <label className="block text-sm text-slate-400 mb-3">Crypto Symbols</label>
                    <input
                      type="text"
                      value={settings.crypto_symbols?.join(', ') || ''}
                      onChange={(e) => setSettings({
                        ...settings,
                        crypto_symbols: e.target.value.split(',').map(s => s.trim().toUpperCase()).filter(s => s)
                      })}
                      className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:outline-none"
                      placeholder="BTC/USD, ETH/USD, SOL/USD"
                    />
                    <p className="text-xs text-slate-500 mt-2">Enter crypto pairs separated by commas (e.g., BTC/USD, ETH/USD)</p>
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Max Crypto Positions</label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="1"
                        max="10"
                        value={settings.crypto_max_positions}
                        onChange={(e) => setSettings({ ...settings, crypto_max_positions: parseInt(e.target.value) })}
                        className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
                      />
                      <span className="text-lg font-semibold w-12 text-right">{settings.crypto_max_positions}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Maximum number of crypto positions at once</p>
                  </div>
                </>
              )}
            </div>
          </div>

          {settings.crypto_trading_enabled && (
            <div className="bg-gradient-to-br from-orange-900/30 to-yellow-900/30 rounded-lg p-6 border border-orange-700/30">
              <h3 className="text-lg font-semibold mb-3">Crypto Trading Info</h3>
              <div className="grid md:grid-cols-2 gap-4 text-sm text-slate-300">
                <div>
                  <p className="font-medium text-white mb-1">24/7 Trading</p>
                  <p>Crypto markets never close. The bot will analyze and trade crypto around the clock, even when stock markets are closed.</p>
                </div>
                <div>
                  <p className="font-medium text-white mb-1">Same Risk Parameters</p>
                  <p>Crypto trades use the same position sizing and risk parameters as your stock trades for consistent risk management.</p>
                </div>
              </div>
            </div>
          )}

          {!settings.crypto_trading_enabled && (
            <div className="bg-blue-900/30 border border-blue-700/50 rounded-lg p-4">
              <p className="text-sm text-blue-300">
                <strong>Note:</strong> Enable crypto trading to allow the bot to trade cryptocurrencies.
                Crypto is available 24/7 through Alpaca's crypto trading infrastructure.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Broker Tab */}
      {activeTab === 'broker' && (
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-green-500" />
              Broker Selection
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <BrokerCard
                name="Alpaca"
                logo="A"
                description="Commission-free trading API"
                status="connected"
                selected={settings.broker === 'alpaca'}
                onSelect={() => setSettings({ ...settings, broker: 'alpaca' })}
              />
              <BrokerCard
                name="Robinhood"
                logo="R"
                description="Popular retail trading app"
                status="coming_soon"
                selected={settings.broker === 'robinhood'}
                onSelect={() => {}}
              />
              <BrokerCard
                name="Fidelity"
                logo="F"
                description="Full-service brokerage"
                status="coming_soon"
                selected={settings.broker === 'fidelity'}
                onSelect={() => {}}
              />
            </div>
          </div>

          <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-lg p-4">
            <p className="text-sm text-yellow-300">
              <strong>Coming Soon:</strong> Robinhood and Fidelity integration is in development.
              Currently, only Alpaca is supported for automated trading.
            </p>
          </div>

          {settings.broker === 'alpaca' && (
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h3 className="text-lg font-semibold mb-4">Alpaca API Status</h3>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-green-400">Connected</span>
              </div>
              <p className="text-sm text-slate-400 mt-2">
                API credentials configured via environment variables.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Toggle Component
function Toggle({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        checked ? 'bg-blue-600' : 'bg-slate-600'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

// Broker Card Component
function BrokerCard({
  name,
  logo,
  description,
  status,
  selected,
  onSelect
}: {
  name: string
  logo: string
  description: string
  status: 'connected' | 'available' | 'coming_soon'
  selected: boolean
  onSelect: () => void
}) {
  const isDisabled = status === 'coming_soon'

  return (
    <button
      onClick={onSelect}
      disabled={isDisabled}
      className={`p-4 rounded-lg border text-left transition-all ${
        selected
          ? 'border-blue-500 bg-blue-500/10'
          : isDisabled
          ? 'border-slate-700 bg-slate-800/50 opacity-60 cursor-not-allowed'
          : 'border-slate-700 bg-slate-800 hover:border-slate-600'
      }`}
    >
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold ${
          selected ? 'bg-blue-600' : 'bg-slate-700'
        }`}>
          {logo}
        </div>
        <div>
          <p className="font-semibold">{name}</p>
          <p className={`text-xs ${
            status === 'connected' ? 'text-green-400' :
            status === 'coming_soon' ? 'text-yellow-400' : 'text-slate-400'
          }`}>
            {status === 'connected' ? 'Connected' : status === 'coming_soon' ? 'Coming Soon' : 'Available'}
          </p>
        </div>
      </div>
      <p className="text-sm text-slate-400">{description}</p>
    </button>
  )
}
