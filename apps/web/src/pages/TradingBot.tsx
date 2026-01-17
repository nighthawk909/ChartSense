/**
 * Trading Bot Dashboard Page
 * Main interface for controlling and monitoring the automated trading bot
 */
import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Brain } from 'lucide-react';

import BotStatusCard from '../components/bot/BotStatusCard';
import BotControls from '../components/bot/BotControls';
import AccountSummary from '../components/bot/AccountSummary';
import CurrentPositions from '../components/bot/CurrentPositions';
import TradeHistory from '../components/bot/TradeHistory';
import PerformanceStats from '../components/bot/PerformanceStats';
import ActivityLog from '../components/bot/ActivityLog';
import AssetClassToggle, { type AssetClassMode } from '../components/bot/AssetClassToggle';
import TickerCarousel, { type TickerItem } from '../components/bot/TickerCarousel';
import AIIntelligenceSidebar from '../components/bot/AIIntelligenceSidebar';

import { botApi, positionsApi, performanceApi } from '../services/botApi';
import type {
  BotStatus,
  AccountSummary as AccountSummaryType,
  Position,
  Trade,
  PerformanceMetrics,
} from '../types/bot';

interface ActivityItem {
  timestamp: string | null;
  type: string;
  message: string;
  level: 'info' | 'warning' | 'error' | 'success';
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type StrategyOverride = 'none' | 'conservative' | 'moderate' | 'aggressive';

export default function TradingBot() {
  // State
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [account, setAccount] = useState<AccountSummaryType | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [tradesTotal, setTradesTotal] = useState(0);
  const [tradesPage, setTradesPage] = useState(1);
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);

  // New UI state
  const [assetMode, setAssetMode] = useState<AssetClassMode>('both');
  const [showAISidebar, setShowAISidebar] = useState(false);
  const [carouselIndex, setCarouselIndex] = useState(0);
  const [newEntriesPaused, setNewEntriesPaused] = useState(false);
  const [currentStrategy, setCurrentStrategy] = useState<StrategyOverride>('moderate');
  const [scanCount, setScanCount] = useState(0);
  const [cardsPerView, setCardsPerView] = useState(4);

  // Responsive cards per view
  useEffect(() => {
    const updateCardsPerView = () => {
      if (window.innerWidth < 640) setCardsPerView(1);
      else if (window.innerWidth < 1024) setCardsPerView(2);
      else setCardsPerView(4);
    };
    updateCardsPerView();
    window.addEventListener('resize', updateCardsPerView);
    return () => window.removeEventListener('resize', updateCardsPerView);
  }, []);

  // Loading states
  const [statusLoading, setStatusLoading] = useState(true);
  const [accountLoading, setAccountLoading] = useState(true);
  const [positionsLoading, setPositionsLoading] = useState(true);
  const [tradesLoading, setTradesLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [activityLoading, setActivityLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // Fetch bot status with diagnostic logging
  const fetchStatus = useCallback(async () => {
    try {
      const data = await botApi.getStatus();
      setStatus(data);
      // Update tactical control states from status
      if (data.new_entries_paused !== undefined) {
        setNewEntriesPaused(data.new_entries_paused);
      }
      if (data.strategy_override) {
        setCurrentStrategy(data.strategy_override as StrategyOverride);
      }
      if (data.total_scans_today !== undefined) {
        setScanCount(data.total_scans_today);
      }
      // Update asset class mode from status
      if (data.asset_class_mode) {
        setAssetMode(data.asset_class_mode as AssetClassMode);
      }
    } catch (err) {
      // Log detailed diagnostics on status fetch failure
      console.error('[TradingBot] Failed to fetch status:', err);
      console.error('[TradingBot] API URL attempted:', `${API_URL}/api/bot/status`);

      // Check if it's a network error vs API error
      if (err instanceof TypeError && err.message.includes('fetch')) {
        console.error('[TradingBot] DIAGNOSIS: Network error - API server may be offline');
        console.error('[TradingBot] Make sure the backend is running: cd api && uvicorn main:app --reload --port 8000');
      }
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

  // Fetch activity log
  const fetchActivity = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/activity`);
      if (response.ok) {
        const data = await response.json();
        setActivities(data.activities || []);
      }
    } catch (err) {
      console.error('Failed to fetch activity:', err);
    } finally {
      setActivityLoading(false);
    }
  }, []);

  // Refresh all data
  const refreshAll = useCallback(() => {
    fetchStatus();
    fetchAccount();
    fetchPositions();
    fetchTrades(1);
    fetchMetrics();
    fetchActivity();
  }, [fetchStatus, fetchAccount, fetchPositions, fetchTrades, fetchMetrics, fetchActivity]);

  // Initial load and polling
  useEffect(() => {
    refreshAll();

    // Poll status every 5 seconds
    const interval = setInterval(() => {
      fetchStatus();
      fetchAccount();
      fetchPositions();
      fetchActivity();
    }, 5000);

    return () => clearInterval(interval);
  }, [refreshAll, fetchStatus, fetchAccount, fetchPositions, fetchActivity]);

  // Bot control handlers with comprehensive diagnostic logging
  const handleStart = async () => {
    console.log('[TradingBot] ========== START BOT INITIATED ==========');
    console.log('[TradingBot] Timestamp:', new Date().toISOString());
    console.log('[TradingBot] API URL:', API_URL);
    console.log('[TradingBot] Current Status:', status?.state);

    setActionLoading(true);
    try {
      console.log('[TradingBot] Calling botApi.start()...');
      const startTime = performance.now();

      const result = await botApi.start();

      const duration = performance.now() - startTime;
      console.log('[TradingBot] Start API Response:', result);
      console.log('[TradingBot] Response time:', duration.toFixed(0), 'ms');

      if (result.success) {
        console.log('[TradingBot] Bot started successfully');
        console.log('[TradingBot] Message:', result.message);
        console.log('[TradingBot] State:', result.state);
      } else {
        console.error('[TradingBot] Bot start returned success=false:', result);
      }

      setTimeout(fetchStatus, 1000);
    } catch (err) {
      console.error('[TradingBot] ========== START FAILED ==========');
      console.error('[TradingBot] Error:', err);
      if (err instanceof Error) {
        console.error('[TradingBot] Error message:', err.message);
        console.error('[TradingBot] Error stack:', err.stack);
      }

      // Try to diagnose the issue
      console.log('[TradingBot] Running diagnostics...');
      try {
        const healthCheck = await fetch(`${API_URL}/health`);
        console.log('[TradingBot] Health check status:', healthCheck.status);
        if (!healthCheck.ok) {
          console.error('[TradingBot] DIAGNOSIS: API server is not responding properly');
        }
      } catch (healthErr) {
        console.error('[TradingBot] DIAGNOSIS: API server appears to be offline');
        console.error('[TradingBot] Cannot reach:', `${API_URL}/health`);
      }
    } finally {
      setActionLoading(false);
      console.log('[TradingBot] ========== START COMPLETE ==========');
    }
  };

  const handleStop = async () => {
    console.log('[TradingBot] ========== STOP BOT INITIATED ==========');
    console.log('[TradingBot] Timestamp:', new Date().toISOString());

    setActionLoading(true);
    try {
      console.log('[TradingBot] Calling botApi.stop()...');
      const result = await botApi.stop();
      console.log('[TradingBot] Stop API Response:', result);
      setTimeout(fetchStatus, 1000);
    } catch (err) {
      console.error('[TradingBot] Failed to stop bot:', err);
    } finally {
      setActionLoading(false);
      console.log('[TradingBot] ========== STOP COMPLETE ==========');
    }
  };

  const handlePause = async () => {
    console.log('[TradingBot] ========== PAUSE BOT INITIATED ==========');
    setActionLoading(true);
    try {
      console.log('[TradingBot] Calling botApi.pause()...');
      const result = await botApi.pause();
      console.log('[TradingBot] Pause API Response:', result);
      setTimeout(fetchStatus, 1000);
    } catch (err) {
      console.error('[TradingBot] Failed to pause bot:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    console.log('[TradingBot] ========== RESUME BOT INITIATED ==========');
    setActionLoading(true);
    try {
      console.log('[TradingBot] Calling botApi.resume()...');
      const result = await botApi.resume();
      console.log('[TradingBot] Resume API Response:', result);
      setTimeout(fetchStatus, 1000);
    } catch (err) {
      console.error('[TradingBot] Failed to resume bot:', err);
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

  // Tactical control handlers
  const handleEmergencyCloseAll = async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/emergency-close-all`, { method: 'POST' });
      if (response.ok) {
        setTimeout(() => {
          fetchPositions();
          fetchStatus();
        }, 1000);
      }
    } catch (err) {
      console.error('Failed to emergency close all:', err);
    }
  };

  const handlePauseNewEntries = async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/pause-entries`, { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        setNewEntriesPaused(data.new_entries_paused);
      }
    } catch (err) {
      console.error('Failed to toggle pause entries:', err);
    }
  };

  const handleStrategyOverride = async (strategy: StrategyOverride) => {
    try {
      const response = await fetch(`${API_URL}/api/bot/strategy-override?strategy=${strategy}`, { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        setCurrentStrategy(data.strategy_override || 'moderate');
      }
    } catch (err) {
      console.error('Failed to set strategy override:', err);
    }
  };

  const handleAssetModeChange = async (mode: AssetClassMode) => {
    setAssetMode(mode);
    try {
      const response = await fetch(`${API_URL}/api/bot/asset-class-mode?mode=${mode}`, { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        console.log('Asset class mode updated:', data);
        // Refresh status to get updated scan progress
        setTimeout(fetchStatus, 500);
      }
    } catch (err) {
      console.error('Failed to set asset class mode:', err);
    }
  };

  const handleToggleAutoTrade = async () => {
    const newValue = !status?.auto_trade_mode;
    console.log('[TradingBot] Toggling auto_trade_mode to:', newValue);
    try {
      const response = await fetch(`${API_URL}/api/bot/auto-trade?enabled=${newValue}`, { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        console.log('[TradingBot] Auto trade mode updated:', data);
        // Refresh status to get updated state
        setTimeout(fetchStatus, 500);
      }
    } catch (err) {
      console.error('Failed to toggle auto trade mode:', err);
    }
  };

  // Build carousel items from both crypto AND stock analysis results
  const carouselItems: TickerItem[] = [];

  // Add crypto items if mode allows
  if ((assetMode === 'crypto' || assetMode === 'both') && status?.crypto_analysis_results) {
    Object.entries(status.crypto_analysis_results).forEach(([symbol, result]) => {
      carouselItems.push({
        symbol,
        analysis: result,
        aiDecision: result.ai_decision,
        assetType: 'crypto',
        // Price would be added here if available in the result
        // For now, indicators might have price data
        price: result.indicators?.close,
        change24h: result.indicators?.change_24h,
      });
    });
  }

  // Add stock items if mode allows
  if ((assetMode === 'stocks' || assetMode === 'both') && status?.stock_analysis_results) {
    Object.entries(status.stock_analysis_results).forEach(([symbol, result]) => {
      carouselItems.push({
        symbol,
        analysis: result,
        aiDecision: result.ai_decision,
        assetType: 'stock',
        price: result.current_price,
        change24h: result.indicators?.change_24h,
      });
    });
  }

  return (
    <div className="space-y-4 sm:space-y-6 max-w-full overflow-x-hidden">
      {/* Header with Asset Toggle and Stats */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-white">Trading Bot</h1>
            <p className="text-sm text-slate-400 hidden sm:block">Automated trading powered by AI</p>
          </div>
          <div className="flex items-center gap-2">
            {/* AI Sidebar Toggle */}
            <button
              onClick={() => setShowAISidebar(!showAISidebar)}
              className={`flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-2 rounded-lg transition-colors ${
                showAISidebar
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-700 text-slate-400 hover:text-white hover:bg-slate-600'
              }`}
            >
              <Brain className="w-4 h-4" />
              <span className="hidden sm:inline">AI Panel</span>
            </button>
            {/* Refresh */}
            <button
              onClick={refreshAll}
              className="flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-2 text-slate-400 hover:text-white
                       hover:bg-slate-700 rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>
        {/* Asset Class Toggle - on its own row for mobile */}
        <div className="overflow-x-auto pb-1">
          <AssetClassToggle
            mode={assetMode}
            onChange={handleAssetModeChange}
            scanCount={scanCount}
            isActive={status?.state === 'RUNNING'}
          />
        </div>
      </div>

      {/* Quick Navigation Carousel - Always show for scanner visibility */}
      <TickerCarousel
        items={carouselItems}
        currentIndex={carouselIndex}
        onIndexChange={setCarouselIndex}
        cardsPerView={cardsPerView}
      />

      {/* Top Row - Status, Controls, Account */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <BotStatusCard status={status} loading={statusLoading} />
        <BotControls
          state={status?.state || 'STOPPED'}
          onStart={handleStart}
          onStop={handleStop}
          onPause={handlePause}
          onResume={handleResume}
          onEmergencyCloseAll={handleEmergencyCloseAll}
          onPauseNewEntries={handlePauseNewEntries}
          onStrategyOverride={handleStrategyOverride}
          onToggleAutoTrade={handleToggleAutoTrade}
          loading={actionLoading}
          newEntriesPaused={newEntriesPaused}
          currentStrategy={currentStrategy}
          hasOpenPositions={positions.length > 0}
          executionLog={status?.execution_log || []}
          aiDecisions={status?.ai_decisions_history || []}
          currentCycle={status?.current_cycle || 'idle'}
          autoTradeMode={status?.auto_trade_mode || false}
          totalScansToday={status?.total_scans_today || scanCount}
        />
        <AccountSummary account={account} loading={accountLoading} />
      </div>

      {/* Middle Row - Positions, Performance, and Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <CurrentPositions
          positions={positions}
          onClosePosition={handleClosePosition}
          loading={positionsLoading}
        />
        <PerformanceStats metrics={metrics} loading={metricsLoading} />
        <ActivityLog activities={activities} loading={activityLoading} />
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

      {/* AI Intelligence Sidebar */}
      <AIIntelligenceSidebar
        isOpen={showAISidebar}
        onToggle={() => setShowAISidebar(!showAISidebar)}
        lastDecision={status?.last_ai_decision}
        decisionHistory={status?.ai_decisions_history || []}
        analysisResults={status?.crypto_analysis_results || {}}
        scanProgress={status?.crypto_scan_progress}
        scanCount={scanCount}
        lastScanTime={status?.crypto_scan_progress?.last_scan_completed}
      />
    </div>
  );
}
