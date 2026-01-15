/**
 * Trading Bot Dashboard Page
 * Main interface for controlling and monitoring the automated trading bot
 */
import { useState, useEffect, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';

import BotStatusCard from '../components/bot/BotStatusCard';
import BotControls from '../components/bot/BotControls';
import AccountSummary from '../components/bot/AccountSummary';
import CurrentPositions from '../components/bot/CurrentPositions';
import TradeHistory from '../components/bot/TradeHistory';
import PerformanceStats from '../components/bot/PerformanceStats';

import { botApi, positionsApi, performanceApi } from '../services/botApi';
import type {
  BotStatus,
  AccountSummary as AccountSummaryType,
  Position,
  Trade,
  PerformanceMetrics,
} from '../types/bot';

export default function TradingBot() {
  // State
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [account, setAccount] = useState<AccountSummaryType | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [tradesTotal, setTradesTotal] = useState(0);
  const [tradesPage, setTradesPage] = useState(1);
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);

  // Loading states
  const [statusLoading, setStatusLoading] = useState(true);
  const [accountLoading, setAccountLoading] = useState(true);
  const [positionsLoading, setPositionsLoading] = useState(true);
  const [tradesLoading, setTradesLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // Fetch bot status
  const fetchStatus = useCallback(async () => {
    try {
      const data = await botApi.getStatus();
      setStatus(data);
    } catch (err) {
      console.error('Failed to fetch status:', err);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  // Fetch account summary
  const fetchAccount = useCallback(async () => {
    try {
      const data = await positionsApi.getAccount();
      setAccount(data);
    } catch (err) {
      console.error('Failed to fetch account:', err);
    } finally {
      setAccountLoading(false);
    }
  }, []);

  // Fetch positions
  const fetchPositions = useCallback(async () => {
    try {
      const data = await positionsApi.getPositions();
      setPositions(data.positions);
    } catch (err) {
      console.error('Failed to fetch positions:', err);
    } finally {
      setPositionsLoading(false);
    }
  }, []);

  // Fetch trades
  const fetchTrades = useCallback(async (page: number) => {
    setTradesLoading(true);
    try {
      const data = await performanceApi.getTrades(page, 10);
      setTrades(data.trades);
      setTradesTotal(data.total_count);
      setTradesPage(page);
    } catch (err) {
      console.error('Failed to fetch trades:', err);
    } finally {
      setTradesLoading(false);
    }
  }, []);

  // Fetch metrics
  const fetchMetrics = useCallback(async () => {
    try {
      const data = await performanceApi.getMetrics(30);
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch metrics:', err);
    } finally {
      setMetricsLoading(false);
    }
  }, []);

  // Refresh all data
  const refreshAll = useCallback(() => {
    fetchStatus();
    fetchAccount();
    fetchPositions();
    fetchTrades(1);
    fetchMetrics();
  }, [fetchStatus, fetchAccount, fetchPositions, fetchTrades, fetchMetrics]);

  // Initial load and polling
  useEffect(() => {
    refreshAll();

    // Poll status every 5 seconds
    const interval = setInterval(() => {
      fetchStatus();
      fetchAccount();
      fetchPositions();
    }, 5000);

    return () => clearInterval(interval);
  }, [refreshAll, fetchStatus, fetchAccount, fetchPositions]);

  // Bot control handlers
  const handleStart = async () => {
    setActionLoading(true);
    try {
      await botApi.start();
      setTimeout(fetchStatus, 1000);
    } catch (err) {
      console.error('Failed to start bot:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStop = async () => {
    setActionLoading(true);
    try {
      await botApi.stop();
      setTimeout(fetchStatus, 1000);
    } catch (err) {
      console.error('Failed to stop bot:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handlePause = async () => {
    setActionLoading(true);
    try {
      await botApi.pause();
      setTimeout(fetchStatus, 1000);
    } catch (err) {
      console.error('Failed to pause bot:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    setActionLoading(true);
    try {
      await botApi.resume();
      setTimeout(fetchStatus, 1000);
    } catch (err) {
      console.error('Failed to resume bot:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleClosePosition = async (symbol: string) => {
    if (!confirm(`Close position in ${symbol}?`)) return;

    try {
      await positionsApi.closePosition(symbol);
      setTimeout(fetchPositions, 1000);
    } catch (err) {
      console.error('Failed to close position:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Trading Bot</h1>
          <p className="text-slate-400">Automated trading powered by AI</p>
        </div>
        <button
          onClick={refreshAll}
          className="flex items-center gap-2 px-4 py-2 text-slate-400 hover:text-white
                   hover:bg-slate-700 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Top Row - Status, Controls, Account */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <BotStatusCard status={status} loading={statusLoading} />
        <BotControls
          state={status?.state || 'STOPPED'}
          onStart={handleStart}
          onStop={handleStop}
          onPause={handlePause}
          onResume={handleResume}
          loading={actionLoading}
        />
        <AccountSummary account={account} loading={accountLoading} />
      </div>

      {/* Middle Row - Positions and Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CurrentPositions
          positions={positions}
          onClosePosition={handleClosePosition}
          loading={positionsLoading}
        />
        <PerformanceStats metrics={metrics} loading={metricsLoading} />
      </div>

      {/* Bottom Row - Trade History */}
      <TradeHistory
        trades={trades}
        totalCount={tradesTotal}
        page={tradesPage}
        pageSize={10}
        onPageChange={fetchTrades}
        loading={tradesLoading}
      />
    </div>
  );
}
