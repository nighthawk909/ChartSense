/**
 * Bot Controls Component
 * Start, Stop, Pause, Resume buttons
 */
import { Play, Square, Pause, RefreshCw } from 'lucide-react';
import type { BotState } from '../../types/bot';

interface BotControlsProps {
  state: BotState;
  onStart: () => void;
  onStop: () => void;
  onPause: () => void;
  onResume: () => void;
  loading?: boolean;
}

export default function BotControls({
  state,
  onStart,
  onStop,
  onPause,
  onResume,
  loading,
}: BotControlsProps) {
  const isRunning = state === 'RUNNING';
  const isPaused = state === 'PAUSED';
  const isStopped = state === 'STOPPED';

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Controls</h3>

      <div className="flex flex-wrap gap-3">
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
            className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700
                     disabled:opacity-50 disabled:cursor-not-allowed
                     text-white font-medium rounded-lg transition-colors"
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
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700
                     disabled:opacity-50 disabled:cursor-not-allowed
                     text-white font-medium rounded-lg transition-colors"
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
            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700
                     disabled:opacity-50 disabled:cursor-not-allowed
                     text-white font-medium rounded-lg transition-colors"
          >
            <Square className="w-4 h-4" />
            Stop
          </button>
        )}
      </div>

      {/* Status Message */}
      {loading && (
        <p className="mt-3 text-sm text-slate-400 flex items-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin" />
          Processing...
        </p>
      )}
    </div>
  );
}
