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
  period?: string;  // 'today', '1W', '1M'
}

interface RecommendedStock {
  symbol: string;
  price: number;
  score: number;
  signal: 'BUY' | 'SELL' | 'HOLD';
  signal_color: string;
  rsi: number;
  macd_bullish: boolean;
  above_sma_20: boolean;
  above_sma_50: boolean;
  week_change_pct: number;
  signals: string[];
}

export default function Markets() {
  const navigate = useNavigate();
  const [assetMode, setAssetMode] = useState<AssetClassMode>('both');
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null);
  const [topGainers, setTopGainers] = useState<TopMover[]>([]);
  const [topLosers, setTopLosers] = useState<TopMover[]>([]);
  const [buyOpportunities, setBuyOpportunities] = useState<RecommendedStock[]>([]);
  const [scanningMarket, setScanningMarket] = useState(false);
  const [executingTrade, setExecutingTrade] = useState<string | null>(null);
  const [moversPeriod, setMoversPeriod] = useState<'today' | '1W' | '1M'>('today');
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

      // Fetch real top movers from API
      try {
        const moversRes = await fetch(`${API_URL}/api/analysis/top-movers?period=${moversPeriod}`);
        if (moversRes.ok) {
          const moversData = await moversRes.json();
          setTopGainers(moversData.gainers || []);
          setTopLosers(moversData.losers || []);
        }
      } catch (err) {
        console.error('Failed to fetch top movers:', err);
      }

    } catch (err) {
      console.error('Failed to fetch market data:', err);
    } finally {
      setLoading(false);
    }
  }, [moversPeriod]);

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

  // Scan market for buy opportunities using AI analysis
  const scanForOpportunities = async () => {
    setScanningMarket(true);
    try {
      const response = await fetch(`${API_URL}/api/analysis/recommendations?limit=10`);
      if (response.ok) {
        const data = await response.json();
        setBuyOpportunities(data.buy_opportunities || []);

        // Also update top gainers/losers from real data
        if (data.top_picks) {
          const gainers = data.top_picks
            .filter((s: RecommendedStock) => s.week_change_pct > 0)
            .map((s: RecommendedStock) => ({
              symbol: s.symbol,
              name: s.symbol,
              price: s.price,
              change: s.week_change_pct,
              changePct: s.week_change_pct,
              volume: 0,
              aiConfidence: s.score,
            }));
          const losers = data.top_picks
            .filter((s: RecommendedStock) => s.week_change_pct < 0)
            .map((s: RecommendedStock) => ({
              symbol: s.symbol,
              name: s.symbol,
              price: s.price,
              change: s.week_change_pct,
              changePct: s.week_change_pct,
              volume: 0,
              aiConfidence: s.score,
            }));
          if (gainers.length > 0) setTopGainers(gainers);
          if (losers.length > 0) setTopLosers(losers);
        }
      }
    } catch (err) {
      console.error('Failed to scan for opportunities:', err);
    } finally {
      setScanningMarket(false);
    }
  };

  // Execute a trade on a BUY opportunity
  const executeTrade = async (stock: RecommendedStock) => {
    setExecutingTrade(stock.symbol);
    try {
      // Call the bot to execute a trade on this symbol
      // Use query params as the endpoint expects
      const params = new URLSearchParams({
        symbol: stock.symbol,
        signal: 'BUY',
        confidence: stock.score.toString(),
        position_size_pct: '5',
      });

      const response = await fetch(`${API_URL}/api/bot/execute-opportunity?${params}`, {
        method: 'POST',
      });

      console.log('[Markets] Execute trade response:', response.status, response.statusText);

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          alert(`✅ Trade executed!\n${result.message}\nQty: ${result.order?.quantity} @ $${result.order?.price?.toFixed(2)}`);
          // Navigate to trading bot to see the position
          navigate('/trading-bot');
        } else {
          alert(`⚠️ Trade not executed: ${result.error || result.message}`);
        }
      } else {
        // Try to parse error response
        let errorMsg = `${response.status}: ${response.statusText}`;
        try {
          const error = await response.json();
          errorMsg = error.detail || error.error || error.message || errorMsg;
        } catch {
          // Response wasn't JSON
        }
        console.error('[Markets] Execute trade failed:', errorMsg);
        alert(`❌ Failed: ${errorMsg}\n\nMake sure the API server is running:\ncd api && uvicorn main:app --reload`);
      }
    } catch (err) {
      console.error('Failed to execute trade:', err);
      alert('❌ Failed to connect to trading bot. Is the API server running?');
    } finally {
      setExecutingTrade(null);
    }
  };

  // Auto-execute best opportunities when bot is running
  const autoExecuteOpportunities = async () => {
    if (!botStatus?.state || botStatus.state !== 'RUNNING') {
      alert('⚠️ Start the Trading Bot first to auto-execute trades');
      navigate('/trading-bot');
      return;
    }

    if (!botStatus?.auto_trade_mode) {
      alert('⚠️ Enable Auto Trade Mode first!\n\nGo to Trading Bot page and click the "Auto Trade" toggle.');
      navigate('/trading-bot');
      return;
    }

    setScanningMarket(true);
    try {
      // Tell the bot to scan and execute on best opportunities
      const params = new URLSearchParams({
        max_trades: '3',
        min_confidence: '70',
        position_size_pct: '5',
      });

      const response = await fetch(`${API_URL}/api/bot/auto-trade-opportunities?${params}`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          const executedList = result.executed?.map((t: any) => `${t.symbol}: ${t.quantity} @ $${t.price?.toFixed(2)}`).join('\n') || '';
          alert(`🚀 ${result.trades_executed || 0} trades executed!\n\n${executedList || result.message}`);
        } else {
          alert(`⚠️ ${result.error || result.message}`);
        }
        fetchMarketData(); // Refresh data
      } else {
        const error = await response.json();
        alert(`❌ Failed: ${error.detail || error.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Failed to auto-execute:', err);
      alert('❌ Failed to connect to trading bot');
    } finally {
      setScanningMarket(false);
    }
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

          {/* Discover Opportunities Button */}
          <button
            onClick={scanForOpportunities}
            disabled={scanningMarket}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              scanningMarket
                ? 'bg-purple-600/50 text-purple-200 cursor-wait'
                : 'bg-purple-600 hover:bg-purple-500 text-white'
            }`}
            title="Scan market for BUY signals"
          >
            <Zap className={`w-4 h-4 ${scanningMarket ? 'animate-pulse' : ''}`} />
            {scanningMarket ? 'Scanning...' : 'Discover'}
          </button>

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

          {/* Top Gainers/Losers with Time Period Selector */}
          <div className="bg-slate-800 rounded-xl p-4">
            {/* Time Period Toggle */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-green-400" />
                <h3 className="font-semibold text-white">Top Gainers</h3>
              </div>
              <div className="flex items-center gap-1 bg-slate-700 rounded-lg p-0.5">
                {(['today', '1W', '1M'] as const).map((period) => (
                  <button
                    key={period}
                    onClick={() => setMoversPeriod(period)}
                    className={`px-2 py-1 text-xs rounded transition-all ${
                      moversPeriod === period
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {period === 'today' ? 'Today' : period}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              {topGainers.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-4">Click Discover to scan for gainers</p>
              ) : (
                topGainers
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
                      period={moversPeriod}
                      onClick={() => handleSymbolSelect(item.symbol)}
                    />
                  ))
              )}
            </div>
          </div>

          {/* Top Losers */}
          <div className="bg-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <TrendingDown className="w-4 h-4 text-red-400" />
              <h3 className="font-semibold text-white">Top Losers</h3>
              <span className="text-xs text-slate-500">({moversPeriod === 'today' ? 'Today' : moversPeriod})</span>
            </div>
            <div className="space-y-2">
              {topLosers.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-4">Click Discover to scan for losers</p>
              ) : (
                topLosers
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
                      period={moversPeriod}
                      onClick={() => handleSymbolSelect(item.symbol)}
                    />
                  ))
              )}
            </div>
          </div>

          {/* BUY Opportunities - Discovered Stocks */}
          {buyOpportunities.length > 0 && (
            <div className="bg-gradient-to-br from-green-900/30 to-emerald-900/30 rounded-xl p-4 border border-green-500/20">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-green-400" />
                  <h3 className="font-semibold text-white">BUY Opportunities</h3>
                  <span className="text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full">
                    {buyOpportunities.length} found
                  </span>
                </div>
                {/* Auto-Execute Button */}
                <button
                  onClick={autoExecuteOpportunities}
                  disabled={scanningMarket}
                  className="px-3 py-1 text-xs bg-green-600 hover:bg-green-500 text-white rounded-lg font-medium transition-all flex items-center gap-1"
                  title="Execute trades on top opportunities"
                >
                  <Zap className="w-3 h-3" />
                  Auto Trade
                </button>
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {buyOpportunities.map((stock) => (
                  <div
                    key={stock.symbol}
                    className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-700/50 transition-colors"
                  >
                    <div
                      onClick={() => handleSymbolSelect(stock.symbol)}
                      className="cursor-pointer flex-1"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white">{stock.symbol}</span>
                        <span className="px-1.5 py-0.5 text-xs bg-green-500/20 text-green-400 rounded">
                          BUY
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        {stock.signals.slice(0, 2).join(' • ')}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <div className="text-white font-medium">${stock.price.toFixed(2)}</div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs ${stock.week_change_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {stock.week_change_pct >= 0 ? '+' : ''}{stock.week_change_pct.toFixed(1)}%
                          </span>
                          <span className="text-xs px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded">
                            {stock.score}%
                          </span>
                        </div>
                      </div>
                      {/* Execute Trade Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          executeTrade(stock);
                        }}
                        disabled={executingTrade === stock.symbol}
                        className={`px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                          executingTrade === stock.symbol
                            ? 'bg-yellow-600/50 text-yellow-200 cursor-wait'
                            : 'bg-green-600 hover:bg-green-500 text-white'
                        }`}
                        title={`Execute BUY on ${stock.symbol}`}
                      >
                        {executingTrade === stock.symbol ? '...' : 'BUY'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

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
              {buyOpportunities.length === 0 && (
                <p className="p-3 bg-slate-700/30 rounded text-center">
                  Click <strong className="text-purple-400">Discover</strong> to scan 50+ stocks for BUY signals
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
  period,
  onClick
}: {
  item: TopMover;
  period?: string;
  onClick: () => void;
}) {
  const isPositive = item.changePct >= 0;
  const periodLabel = period === 'today' ? 'today' : period === '1W' ? 'this week' : 'this month';

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
          {period && <span className="text-slate-500 ml-1">({periodLabel})</span>}
        </div>
      </div>
    </div>
  );
}
