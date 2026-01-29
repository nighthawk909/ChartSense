/**
 * AI Intelligence Sidebar
 * Collapsible sidebar showing live AI analysis and insights
 */
import { useState } from 'react';
import {
  Brain,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  Clock,
  BarChart3,
  Zap,
  Eye,
} from 'lucide-react';
import type { AIDecision, CryptoAnalysisResult, CryptoScanProgress } from '../../types/bot';
import ConfidenceReasoningModal from './ConfidenceReasoningModal';

interface AIIntelligenceSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  lastDecision?: AIDecision | null;
  decisionHistory?: AIDecision[];
  analysisResults?: Record<string, CryptoAnalysisResult>;
  scanProgress?: CryptoScanProgress | null;
  scanCount?: number;
  lastScanTime?: string | null;
}

export default function AIIntelligenceSidebar({
  isOpen,
  onToggle,
  lastDecision,
  decisionHistory = [],
  analysisResults = {},
  scanProgress,
  scanCount = 0,
  lastScanTime,
}: AIIntelligenceSidebarProps) {
  const [selectedDecision, setSelectedDecision] = useState<AIDecision | null>(null);
  const [showReasoningModal, setShowReasoningModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'decisions' | 'analysis' | 'scan'>('decisions');
  const [expandedAnalysis, setExpandedAnalysis] = useState<string | null>(null);

  const handleDecisionClick = (decision: AIDecision) => {
    setSelectedDecision(decision);
    setShowReasoningModal(true);
  };

  // Handle click on crypto analysis card - if it has AI decision, show modal
  const handleAnalysisClick = (symbol: string, result: CryptoAnalysisResult) => {
    if (result.ai_decision) {
      setSelectedDecision(result.ai_decision);
      setShowReasoningModal(true);
    } else {
      // Toggle expanded state for cards without AI decision
      setExpandedAnalysis(expandedAnalysis === symbol ? null : symbol);
    }
  };

  return (
    <>
      {/* Toggle Button (shown when collapsed) - hidden on mobile since there's already a toggle in header */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className="hidden sm:block fixed right-0 top-1/2 -translate-y-1/2 z-40 p-3 bg-purple-600 hover:bg-purple-700
                   text-white rounded-l-lg shadow-lg transition-colors"
          title="Open AI Intelligence Panel"
        >
          <Brain className="w-5 h-5" />
          <ChevronLeft className="w-4 h-4 absolute -left-1 top-1/2 -translate-y-1/2" />
        </button>
      )}

      {/* Sidebar Panel - full screen on mobile */}
      <div
        className={`fixed right-0 top-0 h-full bg-slate-900 border-l border-slate-700 shadow-xl z-50
                  transition-transform duration-300 ease-in-out
                  ${isOpen ? 'translate-x-0' : 'translate-x-full'}
                  w-full sm:w-80 lg:w-96`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400" />
            <h2 className="font-semibold text-white">AI Intelligence</h2>
          </div>
          <div className="flex items-center gap-2">
            {/* Scan Heartbeat */}
            {scanProgress && scanProgress.scan_status === 'scanning' && (
              <div className="flex items-center gap-1.5 text-xs text-blue-400">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                Live
              </div>
            )}
            <button
              onClick={onToggle}
              className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <ChevronRight className="w-5 h-5 text-slate-400" />
            </button>
          </div>
        </div>

        {/* Scan Stats Bar */}
        <div className="flex items-center justify-around p-3 bg-slate-800/50 border-b border-slate-700 text-xs">
          <div className="text-center">
            <span className="text-slate-500 block">Total Scans</span>
            <span className="text-white font-semibold">{scanCount.toLocaleString()}</span>
          </div>
          <div className="text-center">
            <span className="text-slate-500 block">Last Scan</span>
            <span className="text-white font-semibold">
              {lastScanTime ? new Date(lastScanTime).toLocaleTimeString() : '--'}
            </span>
          </div>
          <div className="text-center">
            <span className="text-slate-500 block">Decisions</span>
            <span className="text-white font-semibold">{decisionHistory.length}</span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-700">
          {[
            { id: 'decisions', label: 'Decisions', icon: Target },
            { id: 'analysis', label: 'Analysis', icon: BarChart3 },
            { id: 'scan', label: 'Scan', icon: Activity },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-sm font-medium transition-colors
                       ${activeTab === tab.id
                         ? 'text-purple-400 border-b-2 border-purple-400 bg-purple-500/10'
                         : 'text-slate-400 hover:text-white hover:bg-slate-800'
                       }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100vh-220px)] p-4">
          {/* Decisions Tab */}
          {activeTab === 'decisions' && (
            <div className="space-y-3">
              {/* Latest Decision */}
              {lastDecision && (
                <div className="mb-4">
                  <h3 className="text-xs text-slate-500 uppercase tracking-wide mb-2">Latest</h3>
                  <DecisionCard decision={lastDecision} onClick={() => handleDecisionClick(lastDecision)} />
                </div>
              )}

              {/* Decision History */}
              <h3 className="text-xs text-slate-500 uppercase tracking-wide mb-2">History</h3>
              {decisionHistory.length > 0 ? (
                <div className="space-y-2">
                  {decisionHistory.slice(0, 10).map((decision, idx) => (
                    <DecisionCard
                      key={idx}
                      decision={decision}
                      compact
                      onClick={() => handleDecisionClick(decision)}
                    />
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No decisions yet</p>
              )}
            </div>
          )}

          {/* Analysis Tab */}
          {activeTab === 'analysis' && (
            <div className="space-y-3">
              {/* Signals Above Threshold */}
              <h3 className="text-xs text-slate-500 uppercase tracking-wide mb-2">Signals Above Threshold</h3>
              {(() => {
                const aboveThreshold = Object.entries(analysisResults)
                  .map(([symbol, result]) => ({ symbol, ...result }))
                  .filter(r => r.meets_threshold || r.confidence >= r.threshold)
                  .sort((a, b) => b.confidence - a.confidence);

                return aboveThreshold.length > 0 ? (
                  <div className="space-y-2">
                    {aboveThreshold.map((opp, idx) => {
                      const aiDecision = (opp as CryptoAnalysisResult & { ai_decision?: AIDecision }).ai_decision;
                      const isApproved = aiDecision?.decision === 'APPROVE';
                      const isRejected = aiDecision?.decision === 'REJECT';
                      const isWait = aiDecision?.decision === 'WAIT';
                      const isExpanded = expandedAnalysis === opp.symbol;
                      const hasAiDecision = !!aiDecision;

                      return (
                        <div
                          key={idx}
                          onClick={() => handleAnalysisClick(opp.symbol, opp as CryptoAnalysisResult)}
                          className={`p-3 rounded-lg border transition-colors cursor-pointer hover:border-purple-500/50 ${
                            isApproved ? 'bg-green-500/10 border-green-500/30' :
                            isRejected ? 'bg-red-500/10 border-red-500/30' :
                            isWait ? 'bg-yellow-500/10 border-yellow-500/30' :
                            'bg-slate-800 border-slate-700'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <TrendingUp className={`w-4 h-4 ${
                                isApproved ? 'text-green-500' :
                                isRejected ? 'text-red-500' :
                                'text-yellow-500'
                              }`} />
                              <span className="font-medium text-white">{opp.symbol.replace('/', '')}</span>
                              {aiDecision && (
                                <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${
                                  isApproved ? 'bg-green-500/30 text-green-400' :
                                  isRejected ? 'bg-red-500/30 text-red-400' :
                                  'bg-yellow-500/30 text-yellow-400'
                                }`}>
                                  AI: {aiDecision.decision}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-sm font-semibold ${
                                isApproved ? 'text-green-400' :
                                isRejected ? 'text-red-400' :
                                'text-yellow-400'
                              }`}>
                                {opp.confidence.toFixed(0)}%
                              </span>
                              <span className="text-[10px] text-purple-400">
                                {hasAiDecision ? '↗ details' : '↓ expand'}
                              </span>
                            </div>
                          </div>
                          <p className={`text-xs text-slate-400 ${isExpanded ? '' : 'line-clamp-2'}`}>{opp.reason}</p>

                          {/* Expanded content for cards without AI decision */}
                          {isExpanded && !hasAiDecision && (
                            <div className="mt-2 pt-2 border-t border-slate-600/50">
                              {opp.signals && opp.signals.length > 0 && (
                                <div className="mb-2">
                                  <p className="text-[10px] text-slate-500 uppercase mb-1">Signals</p>
                                  <ul className="text-xs text-slate-300 space-y-0.5">
                                    {opp.signals.map((sig: string, i: number) => (
                                      <li key={i}>• {sig}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {opp.indicators && Object.keys(opp.indicators).length > 0 && (
                                <div>
                                  <p className="text-[10px] text-slate-500 uppercase mb-1">Indicators</p>
                                  <div className="grid grid-cols-2 gap-1 text-xs">
                                    {Object.entries(opp.indicators).slice(0, 6).map(([key, val]) => (
                                      <div key={key} className="flex justify-between">
                                        <span className="text-slate-400">{key}:</span>
                                        <span className="text-white">{typeof val === 'number' ? val.toFixed(2) : String(val)}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          <div className="mt-2 flex items-center gap-2">
                            <div className="flex-1 bg-slate-700 rounded-full h-1.5">
                              <div
                                className={`h-1.5 rounded-full ${
                                  isApproved ? 'bg-green-500' :
                                  isRejected ? 'bg-red-500' :
                                  'bg-yellow-500'
                                }`}
                                style={{ width: `${opp.confidence}%` }}
                              />
                            </div>
                            <span className="text-xs text-slate-500">/{opp.threshold}%</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 text-center py-4">No signals above threshold</p>
                );
              })()}

              {/* All Analysis Results */}
              <h3 className="text-xs text-slate-500 uppercase tracking-wide mt-4 mb-2">All Scanned</h3>
              <div className="space-y-1">
                {Object.entries(analysisResults).map(([symbol, result]) => (
                  <div key={symbol} className="flex items-center justify-between p-2 bg-slate-800/50 rounded">
                    <div className="flex items-center gap-2">
                      {result.meets_threshold ? (
                        <TrendingUp className="w-3 h-3 text-green-500" />
                      ) : result.signal === 'SELL' ? (
                        <TrendingDown className="w-3 h-3 text-red-500" />
                      ) : (
                        <Activity className="w-3 h-3 text-slate-400" />
                      )}
                      <span className="text-sm text-white">{symbol.replace('/', '')}</span>
                    </div>
                    <span className={`text-xs font-medium ${
                      result.meets_threshold ? 'text-green-400' :
                      result.confidence >= 50 ? 'text-yellow-400' : 'text-slate-400'
                    }`}>
                      {result.confidence.toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scan Tab */}
          {activeTab === 'scan' && (
            <div className="space-y-4">
              {scanProgress ? (
                <>
                  {/* Scan Status */}
                  <div className={`p-4 rounded-lg border ${
                    scanProgress.scan_status === 'scanning' ? 'bg-blue-500/10 border-blue-500/30' :
                    scanProgress.scan_status === 'found_opportunity' ? 'bg-yellow-500/10 border-yellow-500/30' :
                    'bg-slate-800 border-slate-700'
                  }`}>
                    <div className="flex items-center gap-2 mb-2">
                      {scanProgress.scan_status === 'scanning' ? (
                        <Activity className="w-5 h-5 text-blue-400 animate-pulse" />
                      ) : scanProgress.scan_status === 'found_opportunity' ? (
                        <Zap className="w-5 h-5 text-yellow-400" />
                      ) : (
                        <Clock className="w-5 h-5 text-slate-400" />
                      )}
                      <span className="font-medium text-white capitalize">
                        {scanProgress.scan_status === 'found_opportunity'
                          ? 'Signal Detected'
                          : scanProgress.scan_status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-slate-300">{scanProgress.scan_summary}</p>
                    {scanProgress.scan_status === 'found_opportunity' && (
                      <p className="text-xs text-yellow-400/70 mt-1">
                        ⚠️ Signal met threshold - check AI Decisions for approval status
                      </p>
                    )}
                  </div>

                  {/* Progress Bar */}
                  <div>
                    <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                      <span>Progress</span>
                      <span>{scanProgress.scanned}/{scanProgress.total}</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-2">
                      <div
                        className="h-2 rounded-full bg-blue-500 transition-all"
                        style={{ width: `${scanProgress.total > 0 ? (scanProgress.scanned / scanProgress.total) * 100 : 0}%` }}
                      />
                    </div>
                  </div>

                  {/* Current Symbol */}
                  {scanProgress.current_symbol && (
                    <div className="flex items-center gap-2 text-sm">
                      <Eye className="w-4 h-4 text-blue-400 animate-pulse" />
                      <span className="text-slate-400">Scanning:</span>
                      <span className="text-white font-medium">{scanProgress.current_symbol}</span>
                    </div>
                  )}

                  {/* Best Opportunity */}
                  {scanProgress.best_opportunity && (
                    <div className="p-3 bg-slate-800 rounded-lg">
                      <h4 className="text-xs text-slate-500 uppercase mb-2">Best Opportunity</h4>
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-white">{scanProgress.best_opportunity.symbol}</span>
                        <span className={`font-semibold ${scanProgress.best_opportunity.meets_threshold ? 'text-green-400' : 'text-yellow-400'}`}>
                          {scanProgress.best_opportunity.confidence.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Next Scan */}
                  {scanProgress.next_scan_in_seconds > 0 && (
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <Clock className="w-4 h-4" />
                      <span>Next scan in {scanProgress.next_scan_in_seconds}s</span>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No scan data available</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Reasoning Modal */}
      {selectedDecision && (
        <ConfidenceReasoningModal
          decision={selectedDecision}
          isOpen={showReasoningModal}
          onClose={() => {
            setShowReasoningModal(false);
            setSelectedDecision(null);
          }}
        />
      )}
    </>
  );
}

// Decision Card Component
function DecisionCard({
  decision,
  compact = false,
  onClick,
}: {
  decision: AIDecision;
  compact?: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
        decision.decision === 'APPROVE' ? 'bg-green-500/10 border-green-500/30 hover:bg-green-500/20' :
        decision.decision === 'WAIT' ? 'bg-yellow-500/10 border-yellow-500/30 hover:bg-yellow-500/20' :
        'bg-red-500/10 border-red-500/30 hover:bg-red-500/20'
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-white">{decision.symbol}</span>
          <span className={`px-1.5 py-0.5 text-xs rounded ${
            decision.decision === 'APPROVE' ? 'bg-green-500/30 text-green-400' :
            decision.decision === 'WAIT' ? 'bg-yellow-500/30 text-yellow-400' :
            'bg-red-500/30 text-red-400'
          }`}>
            {decision.decision}
          </span>
          {decision.time_horizon && (
            <span className={`px-1.5 py-0.5 text-xs rounded ${
              decision.time_horizon === 'SCALP' ? 'bg-red-500/20 text-red-400' :
              decision.time_horizon === 'INTRADAY' ? 'bg-orange-500/20 text-orange-400' :
              'bg-blue-500/20 text-blue-400'
            }`}>
              {decision.time_horizon}
            </span>
          )}
        </div>
        <span className="text-sm font-semibold text-purple-400">{decision.confidence}%</span>
      </div>
      {!compact && (
        <p className="text-xs text-slate-400 line-clamp-2">{decision.reasoning}</p>
      )}
      <div className="mt-1 text-xs text-slate-500">
        {new Date(decision.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}
