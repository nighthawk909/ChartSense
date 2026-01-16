/**
 * Bot Controls Component - Tactical Control Bar
 * Emergency Close All, Pause New Entries, Strategy Override, Start/Stop
 */
import { useState } from 'react';
import {
  Play,
  Square,
  Pause,
  RefreshCw,
  AlertTriangle,
  Ban,
  Settings2,
  ChevronDown,
  Zap,
  Shield,
  TrendingUp
} from 'lucide-react';
import type { BotState } from '../../types/bot';

type StrategyOverride = 'none' | 'conservative' | 'moderate' | 'aggressive';

interface BotControlsProps {
  state: BotState;
  onStart: () => void;
  onStop: () => void;
  onPause: () => void;
  onResume: () => void;
  onEmergencyCloseAll?: () => void;
  onPauseNewEntries?: () => void;
  onStrategyOverride?: (strategy: StrategyOverride) => void;
  loading?: boolean;
  newEntriesPaused?: boolean;
  currentStrategy?: StrategyOverride;
  hasOpenPositions?: boolean;
}

export default function BotControls({
  state,
  onStart,
  onStop,
  onPause,
  onResume,
  onEmergencyCloseAll,
  onPauseNewEntries,
  onStrategyOverride,
  loading,
  newEntriesPaused = false,
  currentStrategy = 'moderate',
  hasOpenPositions = false,
}: BotControlsProps) {
  const isRunning = state === 'RUNNING';
  const isPaused = state === 'PAUSED';
  const isStopped = state === 'STOPPED';
  const [showStrategyMenu, setShowStrategyMenu] = useState(false);
  const [confirmEmergency, setConfirmEmergency] = useState(false);

  const handleEmergencyClose = () => {
    if (confirmEmergency) {
      onEmergencyCloseAll?.();
      setConfirmEmergency(false);
    } else {
      setConfirmEmergency(true);
      // Auto-reset confirmation after 5 seconds
      setTimeout(() => setConfirmEmergency(false), 5000);
    }
  };

  const strategyOptions: { value: StrategyOverride; label: string; icon: typeof Shield; color: string }[] = [
    { value: 'conservative', label: 'Conservative', icon: Shield, color: 'text-blue-400' },
    { value: 'moderate', label: 'Moderate', icon: TrendingUp, color: 'text-yellow-400' },
    { value: 'aggressive', label: 'Aggressive', icon: Zap, color: 'text-red-400' },
  ];

  const currentStrategyOption = strategyOptions.find(s => s.value === currentStrategy) || strategyOptions[1];

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Tactical Controls</h3>

      {/* Main Control Row */}
      <div className="flex flex-wrap gap-2 mb-4">
        {/* Start Button - shown when stopped */}
        {isStopped && (
          <button
            onClick={onStart}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700
                     disabled:opacity-50 disabled:cursor-not-allowed
                     text-white font-medium rounded-lg transition-colors"
          >
            <Play className="w-4 h-4" />
            Start Bot
          </button>
        )}

        {/* Pause Button - shown when running */}
        {isRunning && (
          <button
            onClick={onPause}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-yellow-600 hover:bg-yellow-700
                     disabled:opacity-50 disabled:cursor-not-allowed
                     text-white font-medium rounded-lg transition-colors text-sm"
          >
            <Pause className="w-4 h-4" />
            Pause
          </button>
        )}

        {/* Resume Button - shown when paused */}
        {isPaused && (
          <button
            onClick={onResume}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-700
                     disabled:opacity-50 disabled:cursor-not-allowed
                     text-white font-medium rounded-lg transition-colors text-sm"
          >
            <RefreshCw className="w-4 h-4" />
            Resume
          </button>
        )}

        {/* Stop Button - shown when running or paused */}
        {(isRunning || isPaused) && (
          <button
            onClick={onStop}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-slate-600 hover:bg-slate-500
                     disabled:opacity-50 disabled:cursor-not-allowed
                     text-white font-medium rounded-lg transition-colors text-sm"
          >
            <Square className="w-4 h-4" />
            Stop
          </button>
        )}
      </div>

      {/* Tactical Control Bar - shown when bot is active */}
      {(isRunning || isPaused) && (
        <div className="border-t border-slate-700 pt-4">
          <p className="text-xs text-slate-500 uppercase tracking-wide mb-3">Tactical Actions</p>
          <div className="flex flex-wrap gap-2">
            {/* Emergency Close All */}
            <button
              onClick={handleEmergencyClose}
              disabled={loading || !hasOpenPositions}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all text-sm font-medium
                       disabled:opacity-50 disabled:cursor-not-allowed
                       ${confirmEmergency
                         ? 'bg-red-600 hover:bg-red-700 text-white animate-pulse'
                         : 'bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30'
                       }`}
              title={hasOpenPositions ? 'Close all open positions immediately' : 'No open positions'}
            >
              <AlertTriangle className="w-4 h-4" />
              {confirmEmergency ? 'Confirm Close All' : 'Emergency Close All'}
            </button>

            {/* Pause New Entries */}
            <button
              onClick={onPauseNewEntries}
              disabled={loading}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm font-medium
                       ${newEntriesPaused
                         ? 'bg-orange-500 text-white hover:bg-orange-600'
                         : 'bg-orange-500/20 hover:bg-orange-500/30 text-orange-400 border border-orange-500/30'
                       }`}
              title={newEntriesPaused ? 'Resume new position entries' : 'Pause new position entries but keep monitoring existing'}
            >
              <Ban className="w-4 h-4" />
              {newEntriesPaused ? 'Resume Entries' : 'Pause New Entries'}
            </button>

            {/* Strategy Override Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowStrategyMenu(!showStrategyMenu)}
                disabled={loading}
                className="flex items-center gap-2 px-3 py-2 bg-purple-500/20 hover:bg-purple-500/30
                         text-purple-400 border border-purple-500/30 rounded-lg transition-colors text-sm font-medium
                         disabled:opacity-50 disabled:cursor-not-allowed"
                title="Override trading strategy"
              >
                <Settings2 className="w-4 h-4" />
                <span className="hidden sm:inline">Strategy:</span>
                <currentStrategyOption.icon className={`w-4 h-4 ${currentStrategyOption.color}`} />
                <span className={currentStrategyOption.color}>{currentStrategyOption.label}</span>
                <ChevronDown className={`w-3 h-3 transition-transform ${showStrategyMenu ? 'rotate-180' : ''}`} />
              </button>

              {/* Strategy Dropdown Menu */}
              {showStrategyMenu && (
                <div className="absolute top-full left-0 mt-1 w-48 bg-slate-700 rounded-lg shadow-xl border border-slate-600 z-10">
                  {strategyOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        onStrategyOverride?.(option.value);
                        setShowStrategyMenu(false);
                      }}
                      className={`w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-600 transition-colors text-sm
                               ${currentStrategy === option.value ? 'bg-slate-600' : ''}`}
                    >
                      <option.icon className={`w-4 h-4 ${option.color}`} />
                      <span className="text-white">{option.label}</span>
                      {currentStrategy === option.value && (
                        <span className="ml-auto text-green-400">✓</span>
                      )}
                    </button>
                  ))}
                  <div className="border-t border-slate-600 mt-1 pt-1">
                    <button
                      onClick={() => {
                        onStrategyOverride?.('none');
                        setShowStrategyMenu(false);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-600 transition-colors text-sm text-slate-400"
                    >
                      <RefreshCw className="w-4 h-4" />
                      <span>Reset to Default</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Status Messages */}
      <div className="mt-3 space-y-1">
        {loading && (
          <p className="text-sm text-slate-400 flex items-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Processing...
          </p>
        )}
        {newEntriesPaused && (isRunning || isPaused) && (
          <p className="text-sm text-orange-400 flex items-center gap-2">
            <Ban className="w-4 h-4" />
            New entries paused - monitoring existing positions only
          </p>
        )}
      </div>
    </div>
  );
}
