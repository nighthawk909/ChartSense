/**
 * BacktestForm - Configuration form for running backtests
 */
import { useState, useEffect } from 'react';
import { Play, Loader2, DollarSign, Settings2, TrendingUp } from 'lucide-react';
import backtestApi from '../../services/backtestApi';
import type { BacktestRequest, StrategyInfo } from '../../types/backtest';

interface BacktestFormProps {
  onSubmit: (request: BacktestRequest) => void;
  isLoading: boolean;
}

const POPULAR_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'SPY', 'QQQ'];

export default function BacktestForm({ onSubmit, isLoading }: BacktestFormProps) {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [customSymbol, setCustomSymbol] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState('rsi_oversold');
  const [initialCapital, setInitialCapital] = useState(10000);
  const [positionSizePct, setPositionSizePct] = useState(0.1);
  const [stopLossPct, setStopLossPct] = useState(0.05);
  const [takeProfitPct, setTakeProfitPct] = useState(0.10);

  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const data = await backtestApi.getStrategies();
        setStrategies(data.strategies || []);
        if (data.strategies && data.strategies.length > 0) {
          setSelectedStrategy(data.strategies[0].id);
        }
      } catch (err) {
        console.error('Failed to fetch strategies:', err);
      }
    };
    fetchStrategies();
  }, []);

  const handleCustomSymbolSubmit = () => {
    const symbol = customSymbol.trim().toUpperCase();
    if (symbol) {
      setSelectedSymbol(symbol);
      setCustomSymbol('');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSymbol) return;

    onSubmit({
      symbol: selectedSymbol,
      strategy: selectedStrategy,
      initial_capital: initialCapital,
      position_size_pct: positionSizePct,
      stop_loss_pct: stopLossPct,
      take_profit_pct: takeProfitPct,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Strategy Selection */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Strategy</h3>
        </div>

        <div className="grid grid-cols-1 gap-2">
          {strategies.map((strategy) => (
            <button
              key={strategy.id}
              type="button"
              onClick={() => setSelectedStrategy(strategy.id)}
              className={`p-3 rounded-lg border text-left transition-colors ${
                selectedStrategy === strategy.id
                  ? 'bg-blue-600/20 border-blue-500 text-white'
                  : 'bg-slate-700/50 border-slate-600 text-slate-300 hover:border-slate-500'
              }`}
            >
              <div className="font-medium text-sm">{strategy.name}</div>
              <div className="text-xs text-slate-400 mt-1">{strategy.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Symbol Selection */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-3">Symbol</h3>

        {/* Popular Symbols */}
        <div className="flex flex-wrap gap-2 mb-4">
          {POPULAR_SYMBOLS.map((symbol) => (
            <button
              key={symbol}
              type="button"
              onClick={() => setSelectedSymbol(symbol)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                selectedSymbol === symbol
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {symbol}
            </button>
          ))}
        </div>

        {/* Custom Symbol Input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={customSymbol}
            onChange={(e) => setCustomSymbol(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleCustomSymbolSubmit())}
            placeholder="Custom symbol..."
            className="flex-1 bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm placeholder-slate-400 focus:outline-none focus:border-blue-500"
          />
          <button
            type="button"
            onClick={handleCustomSymbolSubmit}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors"
          >
            Set
          </button>
        </div>

        {/* Selected Symbol */}
        <div className="mt-3 text-center">
          <span className="text-slate-400 text-sm">Testing: </span>
          <span className="text-blue-400 font-semibold text-lg">{selectedSymbol}</span>
        </div>
      </div>

      {/* Parameters */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <div className="flex items-center gap-2 mb-3">
          <Settings2 className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Parameters</h3>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Initial Capital ($)</label>
            <input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(Number(e.target.value))}
              min={1000}
              step={1000}
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Position Size (%)</label>
            <input
              type="number"
              value={positionSizePct * 100}
              onChange={(e) => setPositionSizePct(Number(e.target.value) / 100)}
              min={1}
              max={100}
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Stop Loss (%)</label>
            <input
              type="number"
              value={stopLossPct * 100}
              onChange={(e) => setStopLossPct(Number(e.target.value) / 100)}
              min={1}
              max={50}
              step={0.5}
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Take Profit (%)</label>
            <input
              type="number"
              value={takeProfitPct * 100}
              onChange={(e) => setTakeProfitPct(Number(e.target.value) / 100)}
              min={1}
              max={100}
              step={0.5}
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading || !selectedSymbol}
        className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Running Backtest...
          </>
        ) : (
          <>
            <Play className="w-5 h-5" />
            Run Backtest
          </>
        )}
      </button>
    </form>
  );
}
