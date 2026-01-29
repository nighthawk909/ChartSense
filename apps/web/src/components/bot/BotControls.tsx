/**
 * Bot Controls Component - Compact Tactical Control Bar
 * Emergency Close All, Pause New Entries, Strategy Override, Start/Stop
 * Plus AI decision summaries showing WHY trades are approved/rejected
 */
import { useState } from 'react';
import {
  Play,
  Square,
  Pause,
  RefreshCw,
  AlertTriangle,
  Ban,
  ChevronDown,
  Zap,
  Shield,
  TrendingUp,
  Brain,
  Clock,
  CheckCircle,
  XCircle,
  Activity,
  Loader2,
  Timer,
  Bitcoin,
  BarChart3,
} from 'lucide-react';
import type { BotState, AIDecision, ExecutionLogEntry } from '../../types/bot';

type StrategyOverride = 'none' | 'conservative' | 'moderate' | 'aggressive';

interface ScanProgress {
  total: number;
  scanned: number;
  current_symbol: string | null;
  signals_found: number;
  scan_status: string;
  scan_summary: string;
  last_scan_completed: string | null;
  next_scan_in_seconds: number;
  market_status?: string;
}

interface BotControlsProps {
  state: BotState;
  onStart: () => void;
  onStop: () => void;
  onPause: () => void;
  onResume: () => void;
  onEmergencyCloseAll?: () => void;
  onPauseNewEntries?: () => void;
  onStrategyOverride?: (strategy: StrategyOverride) => void;
  onToggleAutoTrade?: () => void;
  onOpenAIPanel?: () => void;  // NEW: Open AI Intelligence sidebar
  loading?: boolean;
  newEntriesPaused?: boolean;
  currentStrategy?: StrategyOverride;
  hasOpenPositions?: boolean;
  executionLog?: ExecutionLogEntry[];
  aiDecisions?: AIDecision[];
  currentCycle?: string;
  autoTradeMode?: boolean;
  totalScansToday?: number;
  stockScanProgress?: ScanProgress;
  cryptoScanProgress?: ScanProgress;
  assetClassMode?: string;
  cryptoEnabled?: boolean;
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
  onToggleAutoTrade,
  onOpenAIPanel,
  loading,
  newEntriesPaused = false,
  currentStrategy = 'moderate',
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  hasOpenPositions: _hasOpenPositions = false,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  executionLog: _executionLog = [],
  aiDecisions = [],
  currentCycle = 'idle',
  autoTradeMode = false,
  totalScansToday = 0,
  stockScanProgress,
  cryptoScanProgress,
  assetClassMode = 'both',
  cryptoEnabled = false,
}: BotControlsProps) {
  const isRunning = state === 'RUNNING';
  const isPaused = state === 'PAUSED';
  const [showStrategyMenu, setShowStrategyMenu] = useState(false);
  const [confirmEmergency, setConfirmEmergency] = useState(false);
  const [decisionFilter, setDecisionFilter] = useState<'all' | 'APPROVE' | 'REJECT' | 'WAIT'>('all');

  const handleEmergencyClose = () => {
    if (confirmEmergency) {
      onEmergencyCloseAll?.();
      setConfirmEmergency(false);
    } else {
      setConfirmEmergency(true);
      setTimeout(() => setConfirmEmergency(false), 5000);
    }
  };

  const strategyOptions: { value: StrategyOverride; label: string; icon: typeof Shield; color: string }[] = [
    { value: 'conservative', label: 'Conservative', icon: Shield, color: 'text-blue-400' },
    { value: 'moderate', label: 'Moderate', icon: TrendingUp, color: 'text-yellow-400' },
    { value: 'aggressive', label: 'Aggressive', icon: Zap, color: 'text-red-400' },
  ];

  const currentStrategyOption = strategyOptions.find(s => s.value === currentStrategy) || strategyOptions[1];

  // Filter and process AI decisions
  const approvedDecisions = aiDecisions.filter(d => d.decision === 'APPROVE');
  const rejectedDecisions = aiDecisions.filter(d => d.decision === 'REJECT');
  const waitDecisions = aiDecisions.filter(d => d.decision === 'WAIT');

  const approvedCount = approvedDecisions.length;
  const rejectedCount = rejectedDecisions.length;
  const waitCount = waitDecisions.length;

  // Filter decisions based on selected filter
  const filteredDecisions = decisionFilter === 'all'
    ? aiDecisions
    : aiDecisions.filter(d => d.decision === decisionFilter);

  const recentDecisions = filteredDecisions.slice(-12).reverse();

  // Handle clicking on count to filter
  const handleCountClick = (filter: 'all' | 'APPROVE' | 'REJECT' | 'WAIT') => {
    setDecisionFilter(filter);
  };

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      {/* Header Row */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">Tactical Controls</h3>
        <div className="flex gap-1.5">
          {isPaused ? (
            <button onClick={onResume} disabled={loading}
              className="flex items-center gap-1 px-2.5 py-1 bg-yellow-500 text-black rounded text-xs font-medium hover:bg-yellow-400">
              <RefreshCw className="w-3 h-3" /> Resume
            </button>
          ) : isRunning ? (
            <button onClick={onPause} disabled={loading}
              className="flex items-center gap-1 px-2.5 py-1 bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 rounded text-xs font-medium hover:bg-yellow-500/30">
              <Pause className="w-3 h-3" /> Pause
            </button>
          ) : null}
          {(isRunning || isPaused) ? (
            <button onClick={onStop} disabled={loading}
              className="flex items-center gap-1 px-2.5 py-1 bg-red-500/20 text-red-400 border border-red-500/30 rounded text-xs font-medium hover:bg-red-500/30">
              <Square className="w-3 h-3" /> Stop
            </button>
          ) : (
            <button onClick={onStart} disabled={loading}
              className="flex items-center gap-1 px-2.5 py-1 bg-green-500 text-white rounded text-xs font-medium hover:bg-green-600">
              <Play className="w-3 h-3" /> Start
            </button>
          )}
        </div>
      </div>

      {/* Quick Actions Row */}
      {(isRunning || isPaused) && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          <button onClick={handleEmergencyClose} disabled={loading}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium ${
              confirmEmergency ? 'bg-red-500 text-white animate-pulse' : 'bg-red-500/20 text-red-400 border border-red-500/30'
            }`}>
            <AlertTriangle className="w-3 h-3" />
            {confirmEmergency ? 'Confirm Close All?' : 'Emergency Close'}
          </button>
          <button onClick={onPauseNewEntries} disabled={loading}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium ${
              newEntriesPaused ? 'bg-orange-500 text-white' : 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
            }`}>
            <Ban className="w-3 h-3" />
            {newEntriesPaused ? 'Resume Entries' : 'Pause Entries'}
          </button>
          <div className="relative">
            <button onClick={() => setShowStrategyMenu(!showStrategyMenu)}
              className="flex items-center gap-1 px-2 py-1 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded text-[10px] font-medium">
              <currentStrategyOption.icon className={`w-3 h-3 ${currentStrategyOption.color}`} />
              {currentStrategyOption.label}
              <ChevronDown className={`w-2.5 h-2.5 transition-transform ${showStrategyMenu ? 'rotate-180' : ''}`} />
            </button>
            {showStrategyMenu && (
              <div className="absolute top-full left-0 mt-1 w-28 bg-slate-700 rounded shadow-xl border border-slate-600 z-10">
                {strategyOptions.map((option) => (
                  <button key={option.value} onClick={() => { onStrategyOverride?.(option.value); setShowStrategyMenu(false); }}
                    className={`w-full flex items-center gap-1.5 px-2 py-1.5 hover:bg-slate-600 text-[10px] ${currentStrategy === option.value ? 'bg-slate-600' : ''}`}>
                    <option.icon className={`w-3 h-3 ${option.color}`} />
                    <span className="text-white">{option.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stats Row - Responsive grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-2">
        <button onClick={() => handleCountClick('all')}
          className={`rounded p-1.5 text-center transition-colors ${decisionFilter === 'all' ? 'bg-blue-500/30 ring-1 ring-blue-500/50' : 'bg-slate-700/50 hover:bg-slate-700'}`}>
          <div className="text-sm font-bold text-white">{totalScansToday}</div>
          <div className="text-[9px] text-slate-400">Scans</div>
        </button>
        <button onClick={() => handleCountClick('APPROVE')}
          className={`rounded p-1.5 text-center transition-colors ${decisionFilter === 'APPROVE' ? 'bg-green-500/30 ring-1 ring-green-500/50' : 'bg-slate-700/50 hover:bg-slate-700'}`}>
          <div className="text-sm font-bold text-green-400">{approvedCount}</div>
          <div className="text-[9px] text-slate-400">Approved</div>
        </button>
        <button onClick={() => handleCountClick('REJECT')}
          className={`rounded p-1.5 text-center transition-colors ${decisionFilter === 'REJECT' ? 'bg-red-500/30 ring-1 ring-red-500/50' : 'bg-slate-700/50 hover:bg-slate-700'}`}>
          <div className="text-sm font-bold text-red-400">{rejectedCount}</div>
          <div className="text-[9px] text-slate-400">Rejected</div>
        </button>
        <button onClick={() => handleCountClick('WAIT')}
          className={`rounded p-1.5 text-center transition-colors ${decisionFilter === 'WAIT' ? 'bg-yellow-500/30 ring-1 ring-yellow-500/50' : 'bg-slate-700/50 hover:bg-slate-700'}`}>
          <div className="text-sm font-bold text-yellow-400">{waitCount}</div>
          <div className="text-[9px] text-slate-400">Wait</div>
        </button>
      </div>

      {/* Scan Progress Status - Enhanced display */}
      <div className="space-y-1.5 mb-2">
        {/* Stock Scan Progress */}
        {(assetClassMode === 'stocks' || assetClassMode === 'both') && stockScanProgress && (
          <ScanStatusRow
            type="stock"
            progress={stockScanProgress}
          />
        )}

        {/* Crypto Scan Progress */}
        {cryptoEnabled && cryptoScanProgress && (
          <ScanStatusRow
            type="crypto"
            progress={cryptoScanProgress}
          />
        )}

        {/* Fallback cycle display if no scan progress available */}
        {!stockScanProgress && !cryptoScanProgress && (
          <div className="flex items-center gap-1.5 bg-slate-700/30 rounded px-2 py-1.5">
            <Activity className={`w-3.5 h-3.5 flex-shrink-0 ${isRunning ? 'text-green-400 animate-pulse' : 'text-slate-400'}`} />
            <span className="text-[10px] text-slate-300 flex-1 min-w-0" title={currentCycle.replace(/_/g, ' ')}>
              {currentCycle.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </span>
          </div>
        )}
      </div>

      {/* Auto Trade Toggle - Separate row for emphasis */}
      <div className="flex items-center justify-between bg-slate-700/30 rounded px-2 py-1.5 mb-2">
        <span className="text-[10px] text-slate-400">Auto Trading</span>
        <button onClick={onToggleAutoTrade} disabled={loading}
          className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-medium transition-all ${
            autoTradeMode
              ? 'bg-green-500/30 text-green-400 border border-green-500/50'
              : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
          }`}
          title={autoTradeMode ? 'Click to disable auto trading' : 'Click to enable auto trading'}>
          <Zap className={`w-2.5 h-2.5 ${autoTradeMode ? 'animate-pulse' : ''}`} />
          {autoTradeMode ? 'Auto ON' : 'Auto OFF'}
        </button>
      </div>

      {/* Warning when signals exist but auto-trade is off */}
      {!autoTradeMode && approvedCount > 0 && (
        <div className="flex items-center gap-2 p-2 mb-2 bg-yellow-500/10 border border-yellow-500/30 rounded text-xs">
          <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0" />
          <span className="text-yellow-400">
            {approvedCount} trade{approvedCount > 1 ? 's' : ''} approved but Auto Trade is OFF
          </span>
          <button
            onClick={onToggleAutoTrade}
            className="ml-auto px-2 py-0.5 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 rounded text-[10px] font-medium"
          >
            Enable
          </button>
        </div>
      )}

      {/* AI Decisions List - Show only 4 most recent, link to full panel */}
      <div className="space-y-1.5">
        {recentDecisions.length > 0 ? (
          <>
            {recentDecisions.slice(0, 4).map((decision, idx) => (
              <AIDecisionEntry key={idx} decision={decision} />
            ))}
            {/* View all link if more decisions exist */}
            {aiDecisions.length > 4 && onOpenAIPanel && (
              <button
                onClick={onOpenAIPanel}
                className="w-full text-center py-1.5 text-[10px] text-purple-400 hover:text-purple-300 hover:bg-slate-700/30 rounded transition-colors"
              >
                View all {aiDecisions.length} decisions in AI Panel →
              </button>
            )}
          </>
        ) : (
          <div className="flex items-center gap-2 p-2 bg-slate-700/30 rounded text-xs text-slate-400">
            <Brain className={`w-4 h-4 ${isRunning ? 'text-blue-400 animate-pulse' : 'opacity-40'}`} />
            <span>
              {isRunning
                ? 'Scanning for opportunities...'
                : 'Start bot to see AI trade decisions'}
            </span>
          </div>
        )}
      </div>

      {/* Summary Stats at bottom if we have decisions */}
      {aiDecisions.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-700/50 grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="text-[10px] text-slate-500">Approval Rate</div>
            <div className={`text-sm font-bold ${approvedCount > 0 ? 'text-green-400' : 'text-slate-400'}`}>
              {aiDecisions.length > 0 ? ((approvedCount / aiDecisions.length) * 100).toFixed(0) : 0}%
            </div>
          </div>
          <div>
            <div className="text-[10px] text-slate-500">Avg Confidence</div>
            <div className="text-sm font-bold text-blue-400">
              {aiDecisions.length > 0
                ? (aiDecisions.reduce((sum, d) => sum + (d.confidence || 0), 0) / aiDecisions.length).toFixed(0)
                : 0}%
            </div>
          </div>
          <div>
            <div className="text-[10px] text-slate-500">Total Today</div>
            <div className="text-sm font-bold text-white">{totalScansToday}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// Compact AI Decision Entry Component - Click to expand
function AIDecisionEntry({ decision, onClick }: { decision: AIDecision; onClick?: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const time = new Date(decision.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const getDecisionStyle = () => {
    switch (decision.decision) {
      case 'APPROVE': return { bg: 'bg-green-500/10 border-green-500/20', badge: 'bg-green-500/20 text-green-400', icon: <CheckCircle className="w-3 h-3 text-green-400" /> };
      case 'REJECT': return { bg: 'bg-red-500/10 border-red-500/20', badge: 'bg-red-500/20 text-red-400', icon: <XCircle className="w-3 h-3 text-red-400" /> };
      case 'WAIT': return { bg: 'bg-yellow-500/10 border-yellow-500/20', badge: 'bg-yellow-500/20 text-yellow-400', icon: <Clock className="w-3 h-3 text-yellow-400" /> };
      default: return { bg: 'bg-slate-700/50 border-slate-600/30', badge: 'bg-slate-600 text-slate-300', icon: <Brain className="w-3 h-3 text-slate-400" /> };
    }
  };

  const style = getDecisionStyle();
  const hasMoreContent = (decision.reasoning?.length || 0) > 60 || (decision.concerns?.length || 0) > 0;

  return (
    <div
      className={`p-1.5 rounded border cursor-pointer transition-colors hover:bg-slate-700/30 ${style.bg}`}
      onClick={() => {
        if (onClick) {
          onClick();
        } else {
          setExpanded(!expanded);
        }
      }}
    >
      <div className="flex items-start gap-1.5">
        {style.icon}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-medium text-white">{decision.symbol}</span>
            <span className={`px-1 py-0.5 rounded text-[8px] font-medium ${style.badge}`}>{decision.decision}</span>
            {hasMoreContent && (
              <ChevronDown className={`w-3 h-3 text-slate-500 transition-transform ${expanded ? 'rotate-180' : ''}`} />
            )}
            <span className="text-[9px] text-slate-500 ml-auto">{time}</span>
          </div>
          {/* Reasoning - expandable */}
          <p className={`text-[9px] text-slate-400 ${expanded ? '' : 'line-clamp-1'}`}>
            {decision.reasoning}
          </p>
          {/* Expanded content */}
          {expanded && (
            <div className="mt-1.5 pt-1.5 border-t border-slate-600/50 space-y-1">
              {decision.concerns && decision.concerns.length > 0 && (
                <div>
                  <span className="text-[8px] text-slate-500 uppercase">Concerns:</span>
                  <ul className="text-[9px] text-red-400/80 ml-2">
                    {decision.concerns.map((concern, i) => (
                      <li key={i}>• {concern}</li>
                    ))}
                  </ul>
                </div>
              )}
              {decision.wait_for && (
                <div className="text-[9px]">
                  <span className="text-slate-500">Wait for: </span>
                  <span className="text-yellow-400">{decision.wait_for}</span>
                </div>
              )}
              {decision.confidence > 0 && (
                <div className="text-[9px]">
                  <span className="text-slate-500">Confidence: </span>
                  <span className={decision.confidence >= 70 ? 'text-green-400' : 'text-yellow-400'}>
                    {decision.confidence}%
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Compact Scan Status Row for Tactical Controls
function ScanStatusRow({ type, progress }: {
  type: 'stock' | 'crypto';
  progress: ScanProgress;
}) {
  const getStatusIcon = () => {
    switch (progress.scan_status) {
      case 'scanning':
        return <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />;
      case 'found_opportunity':
        return <CheckCircle className="w-3 h-3 text-green-400" />;
      case 'exhausted':
        return <XCircle className="w-3 h-3 text-yellow-400" />;
      case 'market_closed':
        return <Clock className="w-3 h-3 text-orange-400" />;
      case 'at_capacity':
        return <Ban className="w-3 h-3 text-orange-400" />;
      default:
        return <Clock className="w-3 h-3 text-slate-400" />;
    }
  };

  const getStatusColor = () => {
    switch (progress.scan_status) {
      case 'scanning': return 'bg-blue-500/20 border-blue-500/30';
      case 'found_opportunity': return 'bg-green-500/20 border-green-500/30';
      case 'exhausted': return 'bg-yellow-500/20 border-yellow-500/30';
      case 'market_closed': return 'bg-orange-500/20 border-orange-500/30';
      case 'at_capacity': return 'bg-orange-500/20 border-orange-500/30';
      default: return 'bg-slate-700/30 border-slate-600/30';
    }
  };

  const getTypeIcon = () => {
    return type === 'crypto' ?
      <Bitcoin className="w-3 h-3 text-yellow-400" /> :
      <BarChart3 className="w-3 h-3 text-green-400" />;
  };

  const progressPct = progress.total > 0 ? (progress.scanned / progress.total) * 100 : 0;

  return (
    <div className={`rounded px-2 py-1.5 border ${getStatusColor()}`}>
      {/* Header Row */}
      <div className="flex items-center gap-1.5">
        {getTypeIcon()}
        <span className="text-[10px] font-medium text-slate-200 uppercase">
          {type}
        </span>
        {getStatusIcon()}
        <span className="text-[9px] text-slate-400 flex-1 truncate">
          {progress.current_symbol ? `Analyzing ${progress.current_symbol}` :
           progress.scan_status.replace(/_/g, ' ')}
        </span>
        {progress.total > 0 && (
          <span className="text-[9px] text-slate-500">
            {progress.scanned}/{progress.total}
          </span>
        )}
      </div>

      {/* Progress Bar - only show when scanning */}
      {progress.scan_status === 'scanning' && progress.total > 0 && (
        <div className="w-full bg-slate-700 rounded-full h-1 mt-1">
          <div
            className="h-1 rounded-full bg-blue-500 transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      )}

      {/* Status Summary - compact */}
      {progress.scan_summary && (
        <p className="text-[9px] text-slate-400 mt-1 line-clamp-1" title={progress.scan_summary}>
          {progress.scan_summary}
        </p>
      )}

      {/* Next Scan Timer */}
      {progress.next_scan_in_seconds > 0 && progress.scan_status !== 'scanning' && (
        <div className="flex items-center gap-1 mt-1 text-[9px] text-slate-500">
          <Timer className="w-2.5 h-2.5" />
          Next scan in {progress.next_scan_in_seconds}s
        </div>
      )}
    </div>
  );
}
