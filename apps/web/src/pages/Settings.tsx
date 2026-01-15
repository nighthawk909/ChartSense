import { useState, useEffect } from 'react'
import { Save, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface BotSettings {
  risk_per_trade: number
  max_position_size: number
  default_stop_loss_pct: number
  default_take_profit_pct: number
  min_volume: number
  entry_score_threshold: number
  enabled_symbols: string[]
  auto_optimize: boolean
}

export default function Settings() {
  const [settings, setSettings] = useState<BotSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API_URL}/api/settings/`)
      if (response.ok) {
        const data = await response.json()
        setSettings(data.settings || data)
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error)
      setMessage({ type: 'error', text: 'Failed to load settings' })
    } finally {
      setLoading(false)
    }
  }

  const saveSettings = async () => {
    if (!settings) return
    setSaving(true)
    setMessage(null)

    try {
      const response = await fetch(`${API_URL}/api/settings/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
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
        await fetchSettings()
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

  return (
    <div className="max-w-4xl mx-auto space-y-6">
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

      {settings && (
        <div className="space-y-6">
          {/* Risk Management */}
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Risk Management</h2>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Risk Per Trade (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={(settings.risk_per_trade * 100).toFixed(1)}
                  onChange={(e) => setSettings({ ...settings, risk_per_trade: parseFloat(e.target.value) / 100 })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
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
              <div>
                <label className="block text-sm text-slate-400 mb-2">Default Stop Loss (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={(settings.default_stop_loss_pct * 100).toFixed(1)}
                  onChange={(e) => setSettings({ ...settings, default_stop_loss_pct: parseFloat(e.target.value) / 100 })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">Default Take Profit (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={(settings.default_take_profit_pct * 100).toFixed(1)}
                  onChange={(e) => setSettings({ ...settings, default_take_profit_pct: parseFloat(e.target.value) / 100 })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Entry Criteria */}
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
                <p className="text-xs text-slate-500 mt-1">Minimum daily volume required</p>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">Entry Score Threshold</label>
                <input
                  type="number"
                  value={settings.entry_score_threshold}
                  onChange={(e) => setSettings({ ...settings, entry_score_threshold: parseFloat(e.target.value) })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
                <p className="text-xs text-slate-500 mt-1">Minimum signal score (0-100) to enter trade</p>
              </div>
            </div>
          </div>

          {/* Symbols */}
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-semibold mb-4">Trading Symbols</h2>
            <div>
              <label className="block text-sm text-slate-400 mb-2">Enabled Symbols (comma-separated)</label>
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
              <p className="text-xs text-slate-500 mt-1">Symbols the bot will trade</p>
            </div>
          </div>

          {/* Auto Optimize */}
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Auto Optimize</h2>
                <p className="text-sm text-slate-400">Automatically adjust parameters based on performance</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.auto_optimize}
                  onChange={(e) => setSettings({ ...settings, auto_optimize: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-600 peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
