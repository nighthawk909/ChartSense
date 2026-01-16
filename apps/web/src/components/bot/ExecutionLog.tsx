/**
 * Execution Log Component
 * Shows why trades were or weren't executed - for debugging paper trade failures
 */
import { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  ChevronDown,
  ChevronUp,
  Search,
  Filter,
  RefreshCw,
} from 'lucide-react';
import type { ExecutionLogEntry } from '../../types/bot';

interface ExecutionLogProps {
  entries: ExecutionLogEntry[];
  loading?: boolean;
  onRefresh?: () => void;
  onFetchStrongBuyTrace?: () => void;
}

const eventTypeColors: Record<string, string> = {
  ENTRY_SIGNAL: 'bg-blue-500/20 text-blue-400',
  ENTRY_ATTEMPT: 'bg-green-500/20 text-green-400',
  ENTRY_SKIPPED: 'bg-yellow-500/20 text-yellow-400',
  ENTRY_FAILED: 'bg-red-500/20 text-red-400',
  EXIT_SIGNAL: 'bg-purple-500/20 text-purple-400',
  EXIT_EXECUTED: 'bg-green-500/20 text-green-400',
  EMERGENCY_CLOSE: 'bg-red-500/20 text-red-400',
  EMERGENCY_CLOSE_FAILED: 'bg-red-500/20 text-red-400',
};

export default function ExecutionLog({
  entries,
  loading,
  onRefresh,
  onFetchStrongBuyTrace,
}: ExecutionLogProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [searchSymbol, setSearchSymbol] = useState('');

  const filteredEntries = entries.filter((entry) => {
    // Filter by execution status
    if (filter === 'executed' && !entry.executed) return false;
    if (filter === 'skipped' && entry.executed) return false;

    // Filter by symbol search
    if (searchSymbol && !entry.symbol.toLowerCase().includes(searchSymbol.toLowerCase())) {
      return false;
    }

    return true;
  });

  const getEventIcon = (entry: ExecutionLogEntry) => {
    if (entry.executed) {
      return <CheckCircle className="w-4 h-4 text-green-400" />;
    }
    if (entry.event_type.includes('FAILED')) {
      return <XCircle className="w-4 h-4 text-red-400" />;
    }
    if (entry.event_type.includes('SKIPPED')) {
      return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
    }
    return <Info className="w-4 h-4 text-blue-400" />;
  };

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Execution Log</h3>
        <div className="flex items-center gap-2">
          {onFetchStrongBuyTrace && (
            <button
              onClick={onFetchStrongBuyTrace}
              className="px-3 py-1.5 text-xs bg-purple-500/20 text-purple-400 hover:bg-purple-500/30
                       rounded-lg transition-colors flex items-center gap-1"
            >
              <Search className="w-3 h-3" />
              Trace Strong Buys
            </button>
          )}
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-4 h-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-1 bg-slate-700/50 rounded-lg p-1">
          {['all', 'executed', 'skipped'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-xs rounded-md transition-colors capitalize ${
                filter === f
                  ? 'bg-slate-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="flex-1 relative">
          <input
            type="text"
            placeholder="Search symbol..."
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value)}
            className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-1.5 text-sm
                     text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          <Filter className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        </div>
      </div>

      {/* Troubleshooting Tips */}
      <div className="mb-4 p-3 bg-slate-700/30 rounded-lg text-xs">
        <h4 className="font-medium text-slate-300 mb-2">Paper Trade Troubleshooting:</h4>
        <ul className="space-y-1 text-slate-400">
          <li>1. Check buying power vs minimum position size</li>
          <li>2. Verify order type matches asset class requirements</li>
          <li>3. Check if bid/ask spread is within threshold</li>
          <li>4. Ensure signal isn't expired before execution</li>
          <li>5. Confirm API keys have trading permissions enabled</li>
        </ul>
      </div>

      {/* Log Entries */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredEntries.length === 0 ? (
          <p className="text-center text-slate-500 py-4">No execution events found</p>
        ) : (
          filteredEntries.map((entry, idx) => (
            <div
              key={idx}
              className={`rounded-lg border transition-colors ${
                entry.executed
                  ? 'bg-green-500/5 border-green-500/20'
                  : 'bg-slate-700/30 border-slate-600/30'
              }`}
            >
              <button
                onClick={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
                className="w-full p-3 flex items-center justify-between text-left"
              >
                <div className="flex items-center gap-3">
                  {getEventIcon(entry)}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{entry.symbol}</span>
                      <span className={`px-1.5 py-0.5 text-xs rounded ${
                        eventTypeColors[entry.event_type] || 'bg-slate-600 text-slate-300'
                      }`}>
                        {entry.event_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
                      {entry.reason}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </span>
                  {expandedIndex === idx ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </button>

              {/* Expanded Details */}
              {expandedIndex === idx && (
                <div className="px-3 pb-3 border-t border-slate-600/30">
                  <div className="pt-3 space-y-2">
                    <div>
                      <span className="text-xs text-slate-500">Full Reason:</span>
                      <p className="text-sm text-slate-300">{entry.reason}</p>
                    </div>
                    {Object.keys(entry.details).length > 0 && (
                      <div>
                        <span className="text-xs text-slate-500">Details:</span>
                        <div className="mt-1 bg-slate-800 rounded p-2">
                          <pre className="text-xs text-slate-400 overflow-x-auto">
                            {JSON.stringify(entry.details, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>Timestamp: {new Date(entry.timestamp).toLocaleString()}</span>
                      <span>Status: {entry.executed ? 'Executed' : 'Not Executed'}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
