/**
 * Unified Markets Page
 * Single view for Stocks, Crypto, or Hybrid with Global Toggle
 * Replaces separate Crypto tab
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, Activity,
  RefreshCw, Zap, Bitcoin, Briefcase, Shuffle, Brain, Sparkles
} from 'lucide-react';
import HybridWatchlist from '../components/watchlist/HybridWatchlist';
import StockChart from '../components/StockChart';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type AssetClassMode = 'stocks' | 'crypto' | 'both';

interface MarketOverview {
  stocksUp: number;
  stocksDown: number;
  cryptoUp: number;
  cryptoDown: number;
  totalVolume: number;
  marketSentiment: 'bullish' | 'bearish' | 'neutral';
}

interface TopMover {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  volume: number;
  aiConfidence?: number;
}

export default function Markets() {
  useNavigate(); // Keep router context active
  const [assetMode, setAssetMode] = useState<AssetClassMode>('both');
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null);
  const [topGainers, setTopGainers] = useState<TopMover[]>([]);
  const [topLosers, setTopLosers] = useState<TopMover[]>([]);
  const [_searchQuery, _setSearchQuery] = useState(''); // Reserved for search feature
  const [loading, setLoading] = useState(true);
  const [botStatus, setBotStatus] = useState<any>(null);

  // Fetch market data
  const fetchMarketData = useCallback(async () => {
    try {
      // Fetch bot status for AI insights
      const statusRes = await fetch(`${API_URL}/api/bot/status`);
      if (statusRes.ok) {
        const status = await statusRes.json();
        setBotStatus(status);
      }

      // Fetch scan progress
      const scanRes = await fetch(`${API_URL}/api/bot/scan-progress`);
      if (scanRes.ok) {
        const scanData = await scanRes.json();
        // Use scan data to populate market overview
        const stockProgress = scanData.stock_scan_progress || {};
        const cryptoProgress = scanData.crypto_scan_progress || {};

        setMarketOverview({
          stocksUp: stockProgress.signals_found || 0,
          stocksDown: (stockProgress.scanned || 0) - (stockProgress.signals_found || 0),
          cryptoUp: cryptoProgress.signals_found || 0,
          cryptoDown: (cryptoProgress.scanned || 0) - (cryptoProgress.signals_found || 0),
          totalVolume: 0,
          marketSentiment: calculateSentiment(stockProgress, cryptoProgress),
        });
      }

      // Mock top movers for now (would come from real API)
      setTopGainers([
        { symbol: 'NVDA', name: 'NVIDIA', price: 145.50, change: 12.30, changePct: 9.23, volume: 45000000, aiConfidence: 82 },
        { symbol: 'BTC/USD', name: 'Bitcoin', price: 67500, change: 2100, changePct: 3.21, volume: 28000000000, aiConfidence: 75 },
        { symbol: 'AAPL', name: 'Apple', price: 185.20, change: 4.50, changePct: 2.49, volume: 32000000, aiConfidence: 68 },
      ]);
      setTopLosers([
        { symbol: 'TSLA', name: 'Tesla', price: 245.80, change: -8.20, changePct: -3.23, volume: 38000000, aiConfidence: 45 },
        { symbol: 'ETH/USD', name: 'Ethereum', price: 3200, change: -85, changePct: -2.59, volume: 15000000000, aiConfidence: 52 },
      ]);

    } catch (err) {
      console.error('Failed to fetch market data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 15000);
    return () => clearInterval(interval);
  }, [fetchMarketData]);

  // Update bot's asset class mode when toggle changes
  useEffect(() => {
    const updateBotMode = async () => {
      try {
        await fetch(`${API_URL}/api/bot/asset-class-mode?mode=${assetMode}`, {
          method: 'POST'
        });
      } catch (err) {
        console.error('Failed to update bot mode:', err);
      }
    };
    updateBotMode();
  }, [assetMode]);

  const calculateSentiment = (stockProgress: any, cryptoProgress: any): 'bullish' | 'bearish' | 'neutral' => {
    const totalSignals = (stockProgress.signals_found || 0) + (cryptoProgress.signals_found || 0);
    const totalScanned = (stockProgress.scanned || 0) + (cryptoProgress.scanned || 0);
    if (totalScanned === 0) return 'neutral';
    const signalRate = totalSignals / totalScanned;
    if (signalRate > 0.15) return 'bullish';
    if (signalRate < 0.05) return 'bearish';
    return 'neutral';
  };

  const handleSymbolSelect = (symbol: string) => {
    setSelectedSymbol(symbol);
  };

  return (
    <div className="space-y-6">
      {/* Header with Global Toggle */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Markets</h1>
          <p className="text-slate-400">Real-time market data with AI-powered insights</p>
        </div>

        <div className="flex items-center gap-4">
          {/* Global Asset Class Toggle */}
          <div className="flex items-center gap-1 bg-slate-800 rounded-xl p-1">
            <AssetToggleButton
              active={assetMode === 'stocks'}
              onClick={() => setAssetMode('stocks')}
              icon={Briefcase}
              label="Stocks"
            />
            <AssetToggleButton
              active={assetMode === 'crypto'}
              onClick={() => setAssetMode('crypto')}
              icon={Bitcoin}
              label="Crypto"
            />
            <AssetToggleButton
              active={assetMode === 'both'}
              onClick={() => setAssetMode('both')}
              icon={Shuffle}
              label="Hybrid"
              highlight
            />
          </div>

          {/* Refresh Button */}
          <button
            onClick={fetchMarketData}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Refresh Data"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Market Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Bot Scanning Status */}
        <OverviewCard
          title="Scan Status"
          value={botStatus?.current_cycle?.replace('_', ' ') || 'Idle'}
          subValue={`Session: ${botStatus?.current_session || 'N/A'}`}
          icon={Activity}
          color={botStatus?.state === 'RUNNING' ? 'green' : 'yellow'}
        />

        {/* Market Sentiment */}
        <OverviewCard
          title="AI Sentiment"
          value={marketOverview?.marketSentiment?.toUpperCase() || 'NEUTRAL'}
          subValue={`Based on ${(marketOverview?.stocksUp || 0) + (marketOverview?.cryptoUp || 0)} signals`}
          icon={Brain}
          color={marketOverview?.marketSentiment === 'bullish' ? 'green' : marketOverview?.marketSentiment === 'bearish' ? 'red' : 'yellow'}
        />

        {/* Stocks Overview */}
        {assetMode !== 'crypto' && (
          <OverviewCard
            title="Stocks"
            value={`${marketOverview?.stocksUp || 0} Signals`}
            subValue={`${(botStatus?.stock_scan_progress?.scanned || 0)} scanned`}
            icon={Briefcase}
            color="blue"
          />
        )}

        {/* Crypto Overview */}
        {assetMode !== 'stocks' && (
          <OverviewCard
            title="Crypto"
            value={`${marketOverview?.cryptoUp || 0} Signals`}
            subValue={`${(botStatus?.crypto_scan_progress?.scanned || 0)} scanned`}
            icon={Bitcoin}
            color="purple"
          />
        )}

        {/* Best Opportunity */}
        <OverviewCard
          title="Best Opportunity"
          value={
            botStatus?.crypto_scan_progress?.best_opportunity?.symbol ||
            botStatus?.stock_scan_progress?.best_opportunity?.symbol ||
            'None'
          }
          subValue={
            botStatus?.crypto_scan_progress?.best_opportunity?.confidence
              ? `${botStatus.crypto_scan_progress.best_opportunity.confidence.toFixed(0)}% confidence`
              : botStatus?.stock_scan_progress?.best_opportunity?.confidence
                ? `${botStatus.stock_scan_progress.best_opportunity.confidence.toFixed(0)}% confidence`
                : 'Scanning...'
          }
          icon={Sparkles}
          color="purple"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Watchlist (2/3 width) */}
        <div className="lg:col-span-2">
          <HybridWatchlist
            assetClass={assetMode}
            onSymbolSelect={handleSymbolSelect}
            showCarousel={true}
          />
        </div>

        {/* Right Sidebar */}
        <div className="space-y-4">
          {/* Selected Symbol Chart */}
          {selectedSymbol && (
            <div className="bg-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-white">{selectedSymbol}</h3>
                <button
                  onClick={() => setSelectedSymbol(null)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Close
                </button>
              </div>
              <StockChart
                symbol={selectedSymbol.replace('/', '')}
                chartType="candlestick"
                period="1D"
                interval={selectedSymbol.includes('/') ? '15min' : '5min'}
                showRefreshButton={false}
                autoRefreshSeconds={30}
              />
            </div>
          )}

          {/* Top Gainers */}
          <div className="bg-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-4 h-4 text-green-400" />
              <h3 className="font-semibold text-white">Top Gainers</h3>
            </div>
            <div className="space-y-2">
              {topGainers
                .filter(item => {
                  if (assetMode === 'stocks') return !item.symbol.includes('/');
                  if (assetMode === 'crypto') return item.symbol.includes('/');
                  return true;
                })
                .slice(0, 5)
                .map((item) => (
                  <MoverRow
                    key={item.symbol}
                    item={item}
                    onClick={() => handleSymbolSelect(item.symbol)}
                  />
                ))}
            </div>
          </div>

          {/* Top Losers */}
          <div className="bg-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <TrendingDown className="w-4 h-4 text-red-400" />
              <h3 className="font-semibold text-white">Top Losers</h3>
            </div>
            <div className="space-y-2">
              {topLosers
                .filter(item => {
                  if (assetMode === 'stocks') return !item.symbol.includes('/');
                  if (assetMode === 'crypto') return item.symbol.includes('/');
                  return true;
                })
                .slice(0, 5)
                .map((item) => (
                  <MoverRow
                    key={item.symbol}
                    item={item}
                    onClick={() => handleSymbolSelect(item.symbol)}
                  />
                ))}
            </div>
          </div>

          {/* Scan Summary */}
          <div className="bg-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-yellow-400" />
              <h3 className="font-semibold text-white">Scan Summary</h3>
            </div>
            <div className="text-sm text-slate-400 space-y-2">
              {assetMode !== 'crypto' && botStatus?.stock_scan_progress && (
                <p className="p-2 bg-slate-700/50 rounded">
                  <strong className="text-white">Stocks:</strong>{' '}
                  {botStatus.stock_scan_progress.scan_summary || 'Waiting for scan...'}
                </p>
              )}
              {assetMode !== 'stocks' && botStatus?.crypto_scan_progress && (
                <p className="p-2 bg-slate-700/50 rounded">
                  <strong className="text-white">Crypto:</strong>{' '}
                  {botStatus.crypto_scan_progress.scan_summary || 'Waiting for scan...'}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Asset Toggle Button
function AssetToggleButton({
  active,
  onClick,
  icon: Icon,
  label,
  highlight = false
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  highlight?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
        active
          ? highlight
            ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
            : 'bg-blue-600 text-white'
          : 'text-slate-400 hover:text-white hover:bg-slate-700'
      }`}
    >
      <Icon className="w-4 h-4" />
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

// Overview Card
function OverviewCard({
  title,
  value,
  subValue,
  icon: Icon,
  color
}: {
  title: string;
  value: string;
  subValue: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'green' | 'red' | 'yellow' | 'blue' | 'purple';
}) {
  const colorClasses = {
    green: 'text-green-400 bg-green-500/10',
    red: 'text-red-400 bg-red-500/10',
    yellow: 'text-yellow-400 bg-yellow-500/10',
    blue: 'text-blue-400 bg-blue-500/10',
    purple: 'text-purple-400 bg-purple-500/10',
  };

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-slate-400 text-sm">{title}</span>
        <div className={`p-1.5 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-lg font-bold text-white">{value}</div>
      <div className="text-xs text-slate-500">{subValue}</div>
    </div>
  );
}

// Mover Row
function MoverRow({
  item,
  onClick
}: {
  item: TopMover;
  onClick: () => void;
}) {
  const isPositive = item.changePct >= 0;

  return (
    <div
      onClick={onClick}
      className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-700/50 cursor-pointer transition-colors"
    >
      <div className="flex items-center gap-2">
        <span className="font-medium text-white text-sm">{item.symbol}</span>
        {item.aiConfidence && (
          <span className={`text-xs px-1.5 py-0.5 rounded ${
            item.aiConfidence >= 70 ? 'bg-green-500/20 text-green-400' :
            item.aiConfidence >= 50 ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-red-500/20 text-red-400'
          }`}>
            {item.aiConfidence}%
          </span>
        )}
      </div>
      <div className="text-right">
        <div className="text-sm text-white">${item.price.toLocaleString()}</div>
        <div className={`text-xs ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{item.changePct.toFixed(2)}%
        </div>
      </div>
    </div>
  );
}
