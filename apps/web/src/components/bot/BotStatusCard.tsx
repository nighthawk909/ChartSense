/**
 * Bot Status Card Component
 * Shows current bot state, uptime, and activity
 */
import { Activity, Clock, AlertCircle, Zap } from 'lucide-react';
import type { BotStatus } from '../../types/bot';
import { formatUptime, getStateColor } from '../../services/botApi';

interface BotStatusCardProps {
  status: BotStatus | null;
  loading?: boolean;
}

export default function BotStatusCard({ status, loading }: BotStatusCardProps) {
  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 animate-pulse">
        <div className="h-6 bg-slate-700 rounded w-32 mb-4"></div>
        <div className="h-10 bg-slate-700 rounded w-24 mb-2"></div>
        <div className="h-4 bg-slate-700 rounded w-40"></div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="bg-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 text-slate-400">
          <AlertCircle className="w-5 h-5" />
          <span>Unable to fetch bot status</span>
        </div>
      </div>
    );
  }

  const stateColor = getStateColor(status.state);

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Bot Status</h3>
        {status.paper_trading && (
          <span className="px-2 py-1 text-xs font-medium bg-yellow-500/20 text-yellow-400 rounded">
            PAPER TRADING
          </span>
        )}
      </div>

      {/* Status Indicator */}
      <div className="flex items-center gap-3 mb-4">
        <div className={`relative ${stateColor}`}>
          <Activity className="w-8 h-8" />
          {status.state === 'RUNNING' && (
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
          )}
        </div>
        <div>
          <p className={`text-2xl font-bold ${stateColor}`}>{status.state}</p>
          <p className="text-sm text-slate-400">
            {status.state === 'RUNNING' ? 'Actively trading' :
             status.state === 'PAUSED' ? 'Trading paused' :
             status.state === 'ERROR' ? 'Error occurred' : 'Bot is stopped'}
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center gap-2 text-slate-400 mb-1">
            <Clock className="w-4 h-4" />
            <span className="text-sm">Uptime</span>
          </div>
          <p className="text-lg font-semibold text-white">
            {status.uptime_seconds > 0 ? formatUptime(status.uptime_seconds) : '--'}
          </p>
        </div>

        <div className="bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center gap-2 text-slate-400 mb-1">
            <Zap className="w-4 h-4" />
            <span className="text-sm">Activity</span>
          </div>
          <p className="text-sm font-medium text-white truncate">
            {status.current_cycle.replace(/_/g, ' ')}
          </p>
        </div>
      </div>

      {/* Error Message */}
      {status.error_message && (
        <div className="mt-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <p className="text-sm">{status.error_message}</p>
          </div>
        </div>
      )}

      {/* Last Trade */}
      {status.last_trade_time && (
        <p className="mt-4 text-xs text-slate-500">
          Last trade: {new Date(status.last_trade_time).toLocaleString()}
        </p>
      )}
    </div>
  );
}
