/**
 * Bot Status Card Component
 * Shows current bot state, uptime, and activity
 */
import { Activity, Clock, AlertCircle, Zap, TrendingUp, TrendingDown, Minus, Search, Loader2, CheckCircle2, XCircle, Target, Brain, ThumbsUp, ThumbsDown, Pause } from 'lucide-react';
import type { BotStatus, CryptoAnalysisResult, CryptoScanProgress, AIDecision } from '../../types/bot';
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
        <div className="flex items-center gap-2">
          {status.auto_trade_mode && (
            <span className="px-2 py-1 text-xs font-medium bg-purple-500/20 text-purple-400 rounded flex items-center gap-1">
              <Brain className="w-3 h-3" />
              AI CONTROL
            </span>
          )}
          {status.paper_trading && (
            <span className="px-2 py-1 text-xs font-medium bg-yellow-500/20 text-yellow-400 rounded">
              PAPER TRADING
            </span>
          )}
        </div>
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

      {/* Crypto Scan Progress */}
      {status.crypto_trading_enabled && status.crypto_scan_progress && (
        <CryptoScanProgressCard
          progress={status.crypto_scan_progress}
          lastAnalysisTime={status.last_crypto_analysis_time}
        />
      )}

      {/* AI Decision Panel - Shows when auto_trade_mode is enabled */}
      {status.auto_trade_mode && status.last_ai_decision && (
        <AIDecisionCard decision={status.last_ai_decision} />
      )}

      {/* AI Decision History */}
      {status.auto_trade_mode && status.ai_decisions_history && status.ai_decisions_history.length > 0 && (
        <AIDecisionHistory decisions={status.ai_decisions_history} />
      )}

      {/* Crypto Analysis Results */}
      {status.crypto_trading_enabled && status.crypto_analysis_results && (
        <div className="mt-4 pt-4 border-t border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <Search className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-white">Crypto Analysis</span>
            {status.last_crypto_analysis_time && (
              <span className="text-xs text-slate-500 ml-auto">
                {new Date(status.last_crypto_analysis_time).toLocaleTimeString()}
              </span>
            )}
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {Object.entries(status.crypto_analysis_results).map(([symbol, result]) => (
              <CryptoAnalysisItem key={symbol} symbol={symbol} result={result} />
            ))}
            {Object.keys(status.crypto_analysis_results).length === 0 && (
              <p className="text-xs text-slate-500">Waiting for analysis...</p>
            )}
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

function CryptoScanProgressCard({
  progress,
  lastAnalysisTime
}: {
  progress: CryptoScanProgress;
  lastAnalysisTime?: string | null;
}) {
  const getStatusIcon = () => {
    switch (progress.scan_status) {
      case 'scanning':
        return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
      case 'found_opportunity':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case 'exhausted':
        return <XCircle className="w-4 h-4 text-yellow-400" />;
      default:
        return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusColor = () => {
    switch (progress.scan_status) {
      case 'scanning':
        return 'bg-blue-500/20 border-blue-500/30';
      case 'found_opportunity':
        return 'bg-green-500/20 border-green-500/30';
      case 'exhausted':
        return 'bg-yellow-500/20 border-yellow-500/30';
      default:
        return 'bg-slate-700/50 border-slate-600/30';
    }
  };

  const progressPct = progress.total > 0 ? (progress.scanned / progress.total) * 100 : 0;

  return (
    <div className={`mt-4 p-3 rounded-lg border ${getStatusColor()}`}>
      <div className="flex items-center gap-2 mb-2">
        {getStatusIcon()}
        <span className="text-sm font-medium text-white">Crypto Scan</span>
        <span className="text-xs text-slate-400 ml-auto">
          {progress.scanned}/{progress.total} scanned
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-700 rounded-full h-2 mb-2">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${
            progress.scan_status === 'found_opportunity' ? 'bg-green-500' :
            progress.scan_status === 'exhausted' ? 'bg-yellow-500' :
            'bg-blue-500'
          }`}
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Current Symbol Being Scanned */}
      {progress.current_symbol && (
        <div className="flex items-center gap-2 mb-2 text-xs text-blue-300">
          <Loader2 className="w-3 h-3 animate-spin" />
          Analyzing {progress.current_symbol}...
        </div>
      )}

      {/* Scan Summary */}
      <p className="text-xs text-slate-300">{progress.scan_summary}</p>

      {/* Best Opportunity (if below threshold) */}
      {progress.best_opportunity && !progress.best_opportunity.meets_threshold && progress.scan_status === 'exhausted' && (
        <div className="mt-2 p-2 bg-slate-700/50 rounded flex items-center gap-2">
          <Target className="w-3 h-3 text-yellow-400" />
          <span className="text-xs text-slate-300">
            Best: <span className="text-white font-medium">{progress.best_opportunity.symbol}</span>
            {' '}at {progress.best_opportunity.confidence.toFixed(0)}%
            {' '}<span className="text-slate-500">
              ({(progress.best_opportunity.threshold - progress.best_opportunity.confidence).toFixed(0)}% below threshold)
            </span>
          </span>
        </div>
      )}

      {/* Signals Found */}
      {progress.signals_found > 0 && (
        <div className="mt-2 flex items-center gap-1 text-xs text-green-400">
          <CheckCircle2 className="w-3 h-3" />
          {progress.signals_found} signal{progress.signals_found > 1 ? 's' : ''} above threshold
        </div>
      )}
    </div>
  );
}

function CryptoAnalysisItem({ symbol, result }: { symbol: string; result: CryptoAnalysisResult }) {
  const getSignalIcon = () => {
    if (result.signal === 'BUY') return <TrendingUp className="w-3 h-3 text-green-500" />;
    if (result.signal === 'SELL') return <TrendingDown className="w-3 h-3 text-red-500" />;
    return <Minus className="w-3 h-3 text-slate-400" />;
  };

  const getSignalColor = () => {
    if (result.meets_threshold) return 'text-green-400';
    if (result.signal === 'BUY') return 'text-yellow-400';
    if (result.signal === 'SELL') return 'text-red-400';
    return 'text-slate-400';
  };

  return (
    <div className="bg-slate-700/30 rounded p-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {getSignalIcon()}
          <span className="text-sm font-medium text-white">{symbol.replace('/', '')}</span>
        </div>
        <span className={`text-xs font-medium ${getSignalColor()}`}>
          {result.confidence.toFixed(0)}% / {result.threshold.toFixed(0)}%
        </span>
      </div>
      <p className="text-xs text-slate-400 mt-1">{result.reason}</p>
      {/* Show AI decision if available */}
      {result.ai_decision && (
        <div className={`mt-1 flex items-center gap-1 text-xs ${
          result.ai_decision.decision === 'APPROVE' ? 'text-green-400' :
          result.ai_decision.decision === 'WAIT' ? 'text-yellow-400' :
          'text-red-400'
        }`}>
          <Brain className="w-3 h-3" />
          AI: {result.ai_decision.decision}
        </div>
      )}
    </div>
  );
}

function AIDecisionCard({ decision }: { decision: AIDecision }) {
  const getDecisionIcon = () => {
    switch (decision.decision) {
      case 'APPROVE':
        return <ThumbsUp className="w-4 h-4 text-green-400" />;
      case 'REJECT':
        return <ThumbsDown className="w-4 h-4 text-red-400" />;
      case 'WAIT':
        return <Pause className="w-4 h-4 text-yellow-400" />;
      default:
        return <Brain className="w-4 h-4 text-slate-400" />;
    }
  };

  const getDecisionColor = () => {
    switch (decision.decision) {
      case 'APPROVE':
        return 'bg-green-500/20 border-green-500/30';
      case 'REJECT':
        return 'bg-red-500/20 border-red-500/30';
      case 'WAIT':
        return 'bg-yellow-500/20 border-yellow-500/30';
      default:
        return 'bg-slate-700/50 border-slate-600/30';
    }
  };

  return (
    <div className={`mt-4 p-3 rounded-lg border ${getDecisionColor()}`}>
      <div className="flex items-center gap-2 mb-2">
        <Brain className="w-4 h-4 text-purple-400" />
        <span className="text-sm font-medium text-white">Latest AI Decision</span>
        <span className="text-xs text-slate-400 ml-auto">
          {new Date(decision.timestamp).toLocaleTimeString()}
        </span>
      </div>

      <div className="flex items-center gap-2 mb-2">
        {getDecisionIcon()}
        <span className="text-lg font-bold text-white">{decision.symbol}</span>
        <span className={`px-2 py-0.5 text-xs font-medium rounded ${
          decision.decision === 'APPROVE' ? 'bg-green-500/30 text-green-400' :
          decision.decision === 'WAIT' ? 'bg-yellow-500/30 text-yellow-400' :
          'bg-red-500/30 text-red-400'
        }`}>
          {decision.decision}
        </span>
        <span className="text-xs text-slate-400 ml-auto">
          {decision.confidence}% confidence
        </span>
      </div>

      <p className="text-sm text-slate-300 mb-2">{decision.reasoning}</p>

      {decision.concerns && decision.concerns.length > 0 && (
        <div className="mb-2">
          <span className="text-xs text-slate-500">Concerns:</span>
          <ul className="list-disc list-inside text-xs text-slate-400 ml-2">
            {decision.concerns.map((concern, i) => (
              <li key={i}>{concern}</li>
            ))}
          </ul>
        </div>
      )}

      {decision.wait_for && (
        <div className="text-xs text-yellow-400">
          Waiting for: {decision.wait_for}
        </div>
      )}

      {decision.decision === 'APPROVE' && (
        <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
          {decision.suggested_position_size_pct && (
            <div className="bg-slate-700/50 rounded p-1 text-center">
              <span className="text-slate-400">Size</span>
              <p className="text-white font-medium">{(decision.suggested_position_size_pct * 100).toFixed(1)}%</p>
            </div>
          )}
          {decision.suggested_stop_loss_pct && (
            <div className="bg-slate-700/50 rounded p-1 text-center">
              <span className="text-slate-400">Stop</span>
              <p className="text-white font-medium">{(decision.suggested_stop_loss_pct * 100).toFixed(1)}%</p>
            </div>
          )}
          {decision.suggested_take_profit_pct && (
            <div className="bg-slate-700/50 rounded p-1 text-center">
              <span className="text-slate-400">Target</span>
              <p className="text-white font-medium">{(decision.suggested_take_profit_pct * 100).toFixed(1)}%</p>
            </div>
          )}
        </div>
      )}

      <div className="mt-2 flex items-center gap-1 text-xs text-slate-500">
        {decision.ai_generated ? (
          <>
            <CheckCircle2 className="w-3 h-3 text-purple-400" />
            <span>AI Generated ({decision.model})</span>
          </>
        ) : (
          <>
            <AlertCircle className="w-3 h-3 text-yellow-400" />
            <span>Technical Fallback (AI unavailable)</span>
          </>
        )}
      </div>
    </div>
  );
}

function AIDecisionHistory({ decisions }: { decisions: AIDecision[] }) {
  // Sort by timestamp descending and take last 5
  const recentDecisions = [...decisions]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(1, 6); // Skip the first one (shown in AIDecisionCard)

  if (recentDecisions.length === 0) return null;

  return (
    <div className="mt-4 pt-4 border-t border-slate-700">
      <div className="flex items-center gap-2 mb-2">
        <Brain className="w-4 h-4 text-purple-400" />
        <span className="text-sm font-medium text-white">Recent AI Decisions</span>
      </div>
      <div className="space-y-1 max-h-32 overflow-y-auto">
        {recentDecisions.map((decision, idx) => (
          <div key={idx} className="flex items-center gap-2 text-xs bg-slate-700/30 rounded p-1.5">
            {decision.decision === 'APPROVE' ? (
              <ThumbsUp className="w-3 h-3 text-green-400" />
            ) : decision.decision === 'WAIT' ? (
              <Pause className="w-3 h-3 text-yellow-400" />
            ) : (
              <ThumbsDown className="w-3 h-3 text-red-400" />
            )}
            <span className="text-white font-medium">{decision.symbol}</span>
            <span className={`px-1 py-0.5 text-xs rounded ${
              decision.decision === 'APPROVE' ? 'bg-green-500/20 text-green-400' :
              decision.decision === 'WAIT' ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-red-500/20 text-red-400'
            }`}>
              {decision.decision}
            </span>
            <span className="text-slate-500 ml-auto">
              {new Date(decision.timestamp).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
