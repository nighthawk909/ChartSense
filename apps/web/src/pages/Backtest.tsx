/**
 * Backtest Page
 * Run backtests on trading strategies with historical data
 */
import { useState } from 'react';
import { FlaskConical, AlertCircle, Info } from 'lucide-react';
import BacktestForm from '../components/backtest/BacktestForm';
import MetricsPanel from '../components/backtest/MetricsPanel';
import backtestApi from '../services/backtestApi';
import type { BacktestRequest, BacktestResult } from '../types/backtest';

export default function Backtest() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const handleRunBacktest = async (request: BacktestRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      console.log('[Backtest] Starting backtest with config:', request);
      const data = await backtestApi.runBacktest(request);
      console.log('[Backtest] Backtest complete:', data);
      setResult(data);
    } catch (err) {
      console.error('[Backtest] Failed:', err);
      const message = err instanceof Error ? err.message : 'Failed to run backtest';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center gap-3">
          <FlaskConical className="w-8 h-8 text-blue-400" />
          <div>
            <h1 className="text-2xl font-bold">Strategy Backtester</h1>
            <p className="text-sm text-slate-400">
              Test trading strategies on historical data
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Form */}
          <div className="lg:col-span-1">
            <BacktestForm onSubmit={handleRunBacktest} isLoading={isLoading} />
          </div>

          {/* Right Column - Results */}
          <div className="lg:col-span-2 space-y-6">
            {/* Error Display */}
            {error && (
              <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-red-300">Backtest Failed</h4>
                  <p className="text-sm text-red-400 mt-1">{error}</p>
                </div>
              </div>
            )}

            {/* Loading State */}
            {isLoading && (
              <div className="bg-slate-800 rounded-xl p-8 border border-slate-700 text-center">
                <div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">Running Backtest...</h3>
                <p className="text-slate-400 text-sm">
                  Fetching historical data and simulating trades
                </p>
              </div>
            )}

            {/* Empty State */}
            {!isLoading && !result && !error && (
              <div className="bg-slate-800 rounded-xl p-8 border border-slate-700 text-center">
                <FlaskConical className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-300 mb-2">
                  Configure and Run a Backtest
                </h3>
                <p className="text-slate-400 text-sm max-w-md mx-auto">
                  Select a strategy, choose a symbol, and configure your parameters.
                  Then click "Run Backtest" to see how the strategy would have performed.
                </p>
              </div>
            )}

            {/* Results */}
            {result && !isLoading && (
              <>
                {/* Backtest Info Header */}
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700 flex flex-wrap items-center gap-4 text-sm">
                  <div className="flex items-center gap-2 text-slate-300">
                    <Info className="w-4 h-4 text-slate-400" />
                    <span className="font-medium">{result.strategy.replace(/_/g, ' ')}</span>
                  </div>
                  <div className="text-slate-400">|</div>
                  <div className="text-blue-400 font-semibold">
                    {result.symbol}
                  </div>
                </div>

                {/* Metrics */}
                <MetricsPanel result={result} />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
