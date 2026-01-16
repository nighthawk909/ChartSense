/**
 * Advanced Hybrid Watchlist
 * Professional watchlist with Active Positions vs Watch Only segmentation
 * Includes AI Insights Carousel and dynamic ticker promotion
 */
import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Star, StarOff, TrendingUp, TrendingDown, Eye, EyeOff,
  ChevronLeft, ChevronRight, Sparkles, Activity, Clock,
  ArrowUpRight, ArrowDownRight, Brain, AlertCircle, Plus,
  BarChart3, Zap, Target
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface WatchlistItem {
  symbol: string;
  name?: string;
  currentPrice: number;
  change: number;
  changePct: number;
  volume?: number;
  avgVolume?: number;
  // AI Insights
  aiConfidence?: number;
  aiSignal?: 'BUY' | 'SELL' | 'HOLD' | 'NEUTRAL';
  aiReasoning?: string;
  technicalSummary?: string;
  // Position data (if active)
  isActive: boolean;
  entryPrice?: number;
  quantity?: number;
  unrealizedPnl?: number;
  unrealizedPnlPct?: number;
  // Discovery metadata
  isBotDiscovered?: boolean;
  discoveredAt?: string;
  discoveryReason?: string;
}

interface HybridWatchlistProps {
  assetClass?: 'stocks' | 'crypto' | 'both';
  onSymbolSelect?: (symbol: string) => void;
  showCarousel?: boolean;
}

export default function HybridWatchlist({
  assetClass = 'both',
  onSymbolSelect,
  showCarousel = true
}: HybridWatchlistProps) {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [activePositions, setActivePositions] = useState<WatchlistItem[]>([]);
  const [watchOnly, setWatchOnly] = useState<WatchlistItem[]>([]);
  const [discoveries, setDiscoveries] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [carouselIndex, setCarouselIndex] = useState(0);
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'watching' | 'discovered'>('all');
  const carouselRef = useRef<HTMLDivElement>(null);

  // Fetch watchlist data
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch watchlist
        const watchlistRes = await fetch(`${API_URL}/api/watchlist`);
        let watchlistData: WatchlistItem[] = [];
        if (watchlistRes.ok) {
          const data = await watchlistRes.json();
          watchlistData = (data.items || []).map((item: any) => ({
            symbol: item.symbol,
            name: item.name,
            currentPrice: item.current_price || 0,
            change: item.change || 0,
            changePct: item.change_pct || 0,
            volume: item.volume,
            avgVolume: item.avg_volume,
            isActive: false,
            isBotDiscovered: item.bot_discovered || false,
            discoveredAt: item.discovered_at,
            discoveryReason: item.discovery_reason,
          }));
        }

        // Fetch positions
        const positionsRes = await fetch(`${API_URL}/api/positions`);
        if (positionsRes.ok) {
          const posData = await positionsRes.json();
          const positions = posData.positions || [];

          // Mark active positions in watchlist
          positions.forEach((pos: any) => {
            const existing = watchlistData.find(w => w.symbol === pos.symbol);
            if (existing) {
              existing.isActive = true;
              existing.entryPrice = pos.entry_price;
              existing.quantity = pos.quantity;
              existing.unrealizedPnl = pos.unrealized_pnl;
              existing.unrealizedPnlPct = pos.unrealized_pnl_pct;
              existing.currentPrice = pos.current_price;
            } else {
              // Add position to watchlist if not already there
              watchlistData.push({
                symbol: pos.symbol,
                currentPrice: pos.current_price,
                change: 0,
                changePct: 0,
                isActive: true,
                entryPrice: pos.entry_price,
                quantity: pos.quantity,
                unrealizedPnl: pos.unrealized_pnl,
                unrealizedPnlPct: pos.unrealized_pnl_pct,
              });
            }
          });
        }

        // Fetch AI analysis for watchlist items
        const analysisRes = await fetch(`${API_URL}/api/bot/status`);
        if (analysisRes.ok) {
          const botStatus = await analysisRes.json();
          const cryptoAnalysis = botStatus.crypto_analysis_results || {};
          const stockAnalysis = botStatus.stock_analysis_results || {};

          watchlistData.forEach(item => {
            const analysis = cryptoAnalysis[item.symbol] || stockAnalysis[item.symbol];
            if (analysis) {
              item.aiConfidence = analysis.confidence;
              item.aiSignal = analysis.signal;
              item.aiReasoning = analysis.reason;
              item.technicalSummary = analysis.signals?.slice(0, 3).join(' | ');
            }
          });
        }

        // Filter by asset class
        let filtered = watchlistData;
        if (assetClass === 'crypto') {
          filtered = watchlistData.filter(item => item.symbol.includes('/USD') || item.symbol.endsWith('USD'));
        } else if (assetClass === 'stocks') {
          filtered = watchlistData.filter(item => !item.symbol.includes('/USD') && !item.symbol.endsWith('USD'));
        }

        setWatchlist(filtered);
        setActivePositions(filtered.filter(item => item.isActive));
        setWatchOnly(filtered.filter(item => !item.isActive && !item.isBotDiscovered));
        setDiscoveries(filtered.filter(item => item.isBotDiscovered && !item.isActive));
      } catch (err) {
        console.error('Failed to fetch watchlist:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [assetClass]);

  // Get display items based on active tab
  const displayItems = activeTab === 'all' ? watchlist
    : activeTab === 'active' ? activePositions
    : activeTab === 'watching' ? watchOnly
    : discoveries;

  // Carousel items (items with AI insights)
  const carouselItems = watchlist.filter(item => item.aiConfidence !== undefined);

  const handleCarouselPrev = () => {
    setCarouselIndex(prev => (prev > 0 ? prev - 1 : carouselItems.length - 1));
  };

  const handleCarouselNext = () => {
    setCarouselIndex(prev => (prev < carouselItems.length - 1 ? prev + 1 : 0));
  };

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-1/4 mb-4"></div>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-slate-700 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* AI Insights Carousel */}
      {showCarousel && carouselItems.length > 0 && (
        <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 rounded-xl p-4 border border-purple-500/20">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-medium text-purple-300">AI Insights Carousel</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCarouselPrev}
                className="p-1 hover:bg-slate-700 rounded transition-colors"
              >
                <ChevronLeft className="w-4 h-4 text-slate-400" />
              </button>
              <span className="text-xs text-slate-500">
                {carouselIndex + 1} / {carouselItems.length}
              </span>
              <button
                onClick={handleCarouselNext}
                className="p-1 hover:bg-slate-700 rounded transition-colors"
              >
                <ChevronRight className="w-4 h-4 text-slate-400" />
              </button>
            </div>
          </div>

          <div ref={carouselRef} className="overflow-hidden">
            <div
              className="flex transition-transform duration-300"
              style={{ transform: `translateX(-${carouselIndex * 100}%)` }}
            >
              {carouselItems.map((item, idx) => (
                <div key={item.symbol} className="w-full flex-shrink-0 px-1">
                  <InsightCard item={item} onSelect={onSymbolSelect} />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-1">
        <TabButton
          active={activeTab === 'all'}
          onClick={() => setActiveTab('all')}
          label="All"
          count={watchlist.length}
        />
        <TabButton
          active={activeTab === 'active'}
          onClick={() => setActiveTab('active')}
          label="Active"
          count={activePositions.length}
          color="green"
        />
        <TabButton
          active={activeTab === 'watching'}
          onClick={() => setActiveTab('watching')}
          label="Watching"
          count={watchOnly.length}
          color="blue"
        />
        {discoveries.length > 0 && (
          <TabButton
            active={activeTab === 'discovered'}
            onClick={() => setActiveTab('discovered')}
            label="Discovered"
            count={discoveries.length}
            color="purple"
            highlight
          />
        )}
      </div>

      {/* Watchlist Items */}
      <div className="bg-slate-800 rounded-xl overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-slate-700/50 text-xs text-slate-400 uppercase tracking-wide">
          <div className="col-span-3">Symbol</div>
          <div className="col-span-2 text-right">Price</div>
          <div className="col-span-2 text-right">Change</div>
          <div className="col-span-2 text-center">AI Signal</div>
          <div className="col-span-2 text-right">Confidence</div>
          <div className="col-span-1"></div>
        </div>

        {/* Items */}
        <div className="divide-y divide-slate-700">
          {displayItems.length === 0 ? (
            <div className="px-4 py-8 text-center text-slate-400">
              <Eye className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No items in this category</p>
            </div>
          ) : (
            displayItems.map((item) => (
              <WatchlistRow
                key={item.symbol}
                item={item}
                onSelect={onSymbolSelect}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// Tab Button Component
function TabButton({
  active,
  onClick,
  label,
  count,
  color = 'white',
  highlight = false
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
  color?: 'white' | 'green' | 'blue' | 'purple';
  highlight?: boolean;
}) {
  const colorClasses = {
    white: 'text-white',
    green: 'text-green-400',
    blue: 'text-blue-400',
    purple: 'text-purple-400',
  };

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
        active
          ? 'bg-slate-600 text-white'
          : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
      } ${highlight && !active ? 'animate-pulse' : ''}`}
    >
      {label}
      <span className={`text-xs px-1.5 py-0.5 rounded ${
        active ? 'bg-slate-500' : 'bg-slate-700'
      } ${colorClasses[color]}`}>
        {count}
      </span>
    </button>
  );
}

// Insight Card Component
function InsightCard({
  item,
  onSelect
}: {
  item: WatchlistItem;
  onSelect?: (symbol: string) => void;
}) {
  const getSignalColor = (signal?: string) => {
    switch (signal) {
      case 'BUY': return 'text-green-400 bg-green-500/20';
      case 'SELL': return 'text-red-400 bg-red-500/20';
      case 'HOLD': return 'text-yellow-400 bg-yellow-500/20';
      default: return 'text-slate-400 bg-slate-500/20';
    }
  };

  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return 'text-slate-400';
    if (confidence >= 75) return 'text-green-400';
    if (confidence >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div
      onClick={() => onSelect?.(item.symbol)}
      className="bg-slate-800/50 rounded-lg p-4 cursor-pointer hover:bg-slate-700/50 transition-colors"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <span className="font-bold text-white">{item.symbol}</span>
            <span className="text-xs text-slate-400">{item.name}</span>
          </div>
          {item.isBotDiscovered && (
            <span className="px-2 py-0.5 text-xs bg-purple-500/20 text-purple-400 rounded-full flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              New Discovery
            </span>
          )}
        </div>
        <div className="text-right">
          <div className="text-lg font-semibold text-white">${item.currentPrice.toFixed(2)}</div>
          <div className={`text-sm ${item.changePct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {item.changePct >= 0 ? '+' : ''}{item.changePct.toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-sm font-medium ${getSignalColor(item.aiSignal)}`}>
            {item.aiSignal || 'N/A'}
          </span>
          <div className="flex items-center gap-1">
            <Brain className="w-4 h-4 text-purple-400" />
            <span className={`font-semibold ${getConfidenceColor(item.aiConfidence)}`}>
              {item.aiConfidence?.toFixed(0) || '--'}%
            </span>
          </div>
        </div>
        <div className="flex-1 text-xs text-slate-400 truncate">
          {item.technicalSummary || item.aiReasoning || 'No analysis available'}
        </div>
      </div>

      {item.isActive && (
        <div className="mt-3 pt-3 border-t border-slate-700 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Position: {item.quantity} @ ${item.entryPrice?.toFixed(2)}
          </span>
          <span className={`text-sm font-semibold ${(item.unrealizedPnlPct || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {(item.unrealizedPnlPct || 0) >= 0 ? '+' : ''}{item.unrealizedPnlPct?.toFixed(2)}%
          </span>
        </div>
      )}
    </div>
  );
}

// Watchlist Row Component
function WatchlistRow({
  item,
  onSelect
}: {
  item: WatchlistItem;
  onSelect?: (symbol: string) => void;
}) {
  const getSignalColor = (signal?: string) => {
    switch (signal) {
      case 'BUY': return 'text-green-400 bg-green-500/20';
      case 'SELL': return 'text-red-400 bg-red-500/20';
      case 'HOLD': return 'text-yellow-400 bg-yellow-500/20';
      default: return 'text-slate-400 bg-slate-500/20';
    }
  };

  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return 'text-slate-400';
    if (confidence >= 75) return 'text-green-400';
    if (confidence >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div
      onClick={() => onSelect?.(item.symbol)}
      className={`grid grid-cols-12 gap-2 px-4 py-3 hover:bg-slate-700/50 cursor-pointer transition-colors ${
        item.isActive ? 'bg-green-500/5' : ''
      }`}
    >
      {/* Symbol */}
      <div className="col-span-3 flex items-center gap-2">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white">{item.symbol}</span>
            {item.isActive && (
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" title="Active Position"></span>
            )}
            {item.isBotDiscovered && (
              <Sparkles className="w-3 h-3 text-purple-400" title="Bot Discovered" />
            )}
          </div>
          {item.name && (
            <span className="text-xs text-slate-500 truncate max-w-[150px]">{item.name}</span>
          )}
        </div>
      </div>

      {/* Price */}
      <div className="col-span-2 flex items-center justify-end">
        <span className="font-medium text-white">${item.currentPrice.toFixed(2)}</span>
      </div>

      {/* Change */}
      <div className="col-span-2 flex items-center justify-end">
        <div className={`flex items-center gap-1 ${item.changePct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {item.changePct >= 0 ? (
            <ArrowUpRight className="w-3 h-3" />
          ) : (
            <ArrowDownRight className="w-3 h-3" />
          )}
          <span className="text-sm font-medium">
            {item.changePct >= 0 ? '+' : ''}{item.changePct.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* AI Signal */}
      <div className="col-span-2 flex items-center justify-center">
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSignalColor(item.aiSignal)}`}>
          {item.aiSignal || 'N/A'}
        </span>
      </div>

      {/* Confidence */}
      <div className="col-span-2 flex items-center justify-end gap-1">
        <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              (item.aiConfidence || 0) >= 75 ? 'bg-green-500' :
              (item.aiConfidence || 0) >= 50 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${item.aiConfidence || 0}%` }}
          ></div>
        </div>
        <span className={`text-xs font-medium ${getConfidenceColor(item.aiConfidence)}`}>
          {item.aiConfidence?.toFixed(0) || '--'}%
        </span>
      </div>

      {/* Actions */}
      <div className="col-span-1 flex items-center justify-end">
        <Link
          to={item.symbol.includes('/') ? `/crypto` : `/stock/${item.symbol}`}
          onClick={(e) => e.stopPropagation()}
          className="p-1.5 hover:bg-slate-600 rounded transition-colors"
          title="View Details"
        >
          <BarChart3 className="w-4 h-4 text-slate-400" />
        </Link>
      </div>
    </div>
  );
}
