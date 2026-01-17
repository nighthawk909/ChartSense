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
} from 'lucide-react';
import type { BotState, AIDecision, ExecutionLogEntry } from '../../types/bot';

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
  onToggleAutoTrade?: () => void;
  loading?: boolean;
  newEntriesPaused?: boolean;
  currentStrategy?: StrategyOverride;
  hasOpenPositions?: boolean;
  executionLog?: ExecutionLogEntry[];
  aiDecisions?: AIDecision[];
  currentCycle?: string;
  autoTradeMode?: boolean;
  totalScansToday?: number;
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

      {/* Stats Row - Compact 4-column grid */}
      <div className="grid grid-cols-4 gap-1.5 mb-2">
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

      {/* Cycle Status + Auto Trade Toggle - Single compact row */}
      <div className="flex items-center gap-2 bg-slate-700/30 rounded px-2 py-1.5 mb-2">
        <Activity className={`w-3.5 h-3.5 ${isRunning ? 'text-green-400 animate-pulse' : 'text-slate-400'}`} />
        <span className="text-[10px] text-slate-300 truncate flex-1">
          {currentCycle.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
        </span>
        <button onClick={onToggleAutoTrade} disabled={loading}
          className={`flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-medium transition-all ${
            autoTradeMode
              ? 'bg-green-500/30 text-green-400 border border-green-500/50'
              : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
          }`}
          title={autoTradeMode ? 'Click to disable auto trading' : 'Click to enable auto trading'}>
          <Zap className={`w-2.5 h-2.5 ${autoTradeMode ? 'animate-pulse' : ''}`} />
          {autoTradeMode ? 'Auto ON' : 'Auto OFF'}
        </button>
      </div>

      {/* AI Decisions List - Show all recent decisions without scroll */}
      <div className="space-y-1.5">
        {recentDecisions.length > 0 ? (
          recentDecisions.map((decision, idx) => (
            <AIDecisionEntry key={idx} decision={decision} />
          ))
        ) : (
          <div className="text-center py-6 text-slate-500 text-xs">
            <Brain className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p>No AI decisions yet</p>
            <p className="text-[10px] mt-1">Start scanning to see AI trade analysis</p>
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

// Compact AI Decision Entry Component
function AIDecisionEntry({ decision }: { decision: AIDecision }) {
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

  return (
    <div className={`flex items-start gap-1.5 p-1.5 rounded border ${style.bg}`}>
      {style.icon}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-medium text-white">{decision.symbol}</span>
          <span className={`px-1 py-0.5 rounded text-[8px] font-medium ${style.badge}`}>{decision.decision}</span>
          <span className="text-[9px] text-slate-500 ml-auto">{time}</span>
        </div>
        <p className="text-[9px] text-slate-400 truncate" title={decision.reasoning}>
          {decision.reasoning?.slice(0, 60)}...
        </p>
      </div>
    </div>
  );
}
