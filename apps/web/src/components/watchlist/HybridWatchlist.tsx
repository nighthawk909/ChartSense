/**
 * Advanced Hybrid Watchlist
 * Professional watchlist with Active Positions vs Watch Only segmentation
 * Includes AI Insights Carousel and dynamic ticker promotion
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Eye, ChevronLeft, ChevronRight, Sparkles,
  ArrowUpRight, ArrowDownRight, Brain,
  BarChart3, Flag
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Format pattern type to human-readable name
function formatPatternName(patternType: string): string {
  const patternNames: Record<string, string> = {
    'BULL_FLAG': 'Bull Flag',
    'BEAR_FLAG': 'Bear Flag',
    'GOLDEN_CROSS': 'Golden Cross',
    'DEATH_CROSS': 'Death Cross',
    'DI_BULLISH_CROSS': 'DI Bullish Cross',
    'DI_BEARISH_CROSS': 'DI Bearish Cross',
    'BB_UPPER_BREAKOUT': 'BB Breakout',
    'BB_LOWER_TOUCH': 'BB Bounce Setup',
    'MACD_BULLISH_CROSS': 'MACD Bullish',
    'MACD_BEARISH_CROSS': 'MACD Bearish',
  };
  return patternNames[patternType] || patternType.replace(/_/g, ' ');
}

interface PatternInfo {
  type: string;
  signal: 'BUY' | 'SELL' | 'WATCH' | 'BOUNCE_POSSIBLE';
  strength: 'strong' | 'moderate' | 'weak';
}

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
  // Pattern detection (for Smart Carousel)
  detectedPatterns?: PatternInfo[];
  primaryPattern?: string;
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

        // Fetch AI analysis and patterns for each watchlist item
        // This works even when the bot isn't running
        const analysisPromises = watchlistData.map(async (item) => {
          try {
            // Check if crypto symbol
            const isCrypto = item.symbol.includes('/') || item.symbol.endsWith('USD') || item.symbol.endsWith('USDT');

            if (isCrypto) {
              // Fetch crypto analysis from crypto API
              const [analysisRes, patternsRes] = await Promise.all([
                fetch(`${API_URL}/api/crypto/analyze/${item.symbol}`),
                fetch(`${API_URL}/api/crypto/patterns/${item.symbol}?interval=1hour`)
              ]);

              if (analysisRes.ok) {
                const analysis = await analysisRes.json();
                const recToSignal: Record<string, 'BUY' | 'SELL' | 'HOLD' | 'NEUTRAL'> = {
                  'STRONG_BUY': 'BUY',
                  'BUY': 'BUY',
                  'LEAN_BUY': 'BUY',
                  'STRONG_SELL': 'SELL',
                  'SELL': 'SELL',
                  'LEAN_SELL': 'SELL',
                  'HOLD': 'HOLD',
                };
                item.aiConfidence = analysis.score;
                item.aiSignal = recToSignal[analysis.recommendation] || 'NEUTRAL';
                item.aiReasoning = analysis.signals?.slice(0, 2).join(' | ') || 'Crypto analysis';
                item.technicalSummary = analysis.signals?.slice(0, 3).join(' | ');
              }

              // Process crypto patterns
              if (patternsRes.ok) {
                const patternData = await patternsRes.json();
                if (patternData.patterns && patternData.patterns.length > 0) {
                  item.detectedPatterns = patternData.patterns;
                  const strongPatterns = patternData.patterns.filter((p: PatternInfo) => p.strength === 'strong');
                  const primaryPatternObj = strongPatterns.length > 0 ? strongPatterns[0] : patternData.patterns[0];
                  item.primaryPattern = formatPatternName(primaryPatternObj.type);
                }
              }
            } else {
              // Fetch stock analysis from stock AI endpoint
              const [insightRes, patternsRes] = await Promise.all([
                fetch(`${API_URL}/api/analysis/ai-insight/${item.symbol}`),
                fetch(`${API_URL}/api/analysis/adaptive-indicators/${item.symbol}?interval=5min`)
              ]);

              // Process AI insight
              if (insightRes.ok) {
                const insight = await insightRes.json();
                const recToSignal: Record<string, 'BUY' | 'SELL' | 'HOLD' | 'NEUTRAL'> = {
                  'STRONG BUY': 'BUY',
                  'BUY': 'BUY',
                  'STRONG SELL': 'SELL',
                  'SELL': 'SELL',
                  'HOLD': 'HOLD',
                };
                item.aiConfidence = insight.score;
                item.aiSignal = recToSignal[insight.recommendation] || 'NEUTRAL';
                item.aiReasoning = insight.action;
                item.technicalSummary = insight.signals?.slice(0, 2).join(' | ') || insight.insight?.substring(0, 80);
              }

              // Process patterns from adaptive indicators
              if (patternsRes.ok) {
                const adaptiveData = await patternsRes.json();
                if (adaptiveData.patterns && adaptiveData.patterns.length > 0) {
                  item.detectedPatterns = adaptiveData.patterns;
                  // Get the primary (strongest) pattern
                  const strongPatterns = adaptiveData.patterns.filter((p: PatternInfo) => p.strength === 'strong');
                  const primaryPatternObj = strongPatterns.length > 0 ? strongPatterns[0] : adaptiveData.patterns[0];
                  item.primaryPattern = formatPatternName(primaryPatternObj.type);
                }
              }
            }
          } catch (err) {
            console.debug(`Failed to fetch analysis for ${item.symbol}:`, err);
          }
        });

        // Wait for all analysis to complete (with timeout)
        await Promise.race([
          Promise.allSettled(analysisPromises),
          new Promise(resolve => setTimeout(resolve, 10000)) // 10 second timeout for patterns
        ]);

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
    // Step back by 3 cards
    setCarouselIndex(prev => {
      const newIndex = prev - 3;
      if (newIndex < 0) {
        // Wrap to last page
        const lastPageStart = Math.floor((carouselItems.length - 1) / 3) * 3;
        return Math.max(0, lastPageStart);
      }
      return newIndex;
    });
  };

  const handleCarouselNext = () => {
    // Step forward by 3 cards
    setCarouselIndex(prev => {
      const newIndex = prev + 3;
      if (newIndex >= carouselItems.length) {
        return 0; // Wrap to beginning
      }
      return newIndex;
    });
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
      {/* AI Insights Carousel - Shows 3 cards at once on desktop, 1 on mobile */}
      {showCarousel && carouselItems.length > 0 && (
        <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 rounded-xl p-4 border border-purple-500/20">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-medium text-purple-300">AI Insights ({carouselItems.length} symbols)</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCarouselPrev}
                className="p-1.5 hover:bg-slate-700 rounded transition-colors"
              >
                <ChevronLeft className="w-5 h-5 text-slate-400" />
              </button>
              <span className="text-xs text-slate-500">
                {Math.floor(carouselIndex / 3) + 1} / {Math.ceil(carouselItems.length / 3)}
              </span>
              <button
                onClick={handleCarouselNext}
                className="p-1.5 hover:bg-slate-700 rounded transition-colors"
              >
                <ChevronRight className="w-5 h-5 text-slate-400" />
              </button>
            </div>
          </div>

          {/* Grid-based carousel showing 3 cards at a time */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {carouselItems
              .slice(carouselIndex, carouselIndex + 3)
              .map((item) => (
                <InsightCard key={item.symbol} item={item} onSelect={onSymbolSelect} />
              ))}
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
        {/* Header - fully responsive grid that scales with container */}
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr_0.8fr_1.2fr_32px] gap-1 sm:gap-2 px-2 sm:px-4 py-2 bg-slate-700/50 text-xs text-slate-400 uppercase tracking-wide">
          <div>Symbol</div>
          <div className="text-right">Price</div>
          <div className="text-right hidden sm:block">Change</div>
          <div className="text-center">Signal</div>
          <div className="text-right hidden md:block">Conf.</div>
          <div className="text-center hidden lg:block">Pattern</div>
          <div></div>
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

      {/* Smart Carousel Format: Symbol - Confidence% - Pattern */}
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
          {/* Pattern Badge - Key Feature of Smart Carousel */}
          {item.primaryPattern && (
            <span className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded flex items-center gap-1">
              <Flag className="w-3 h-3" />
              {item.primaryPattern}
            </span>
          )}
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

  // Get pattern badge color based on signal type
  const getPatternBadge = (pattern?: string, patterns?: PatternInfo[]) => {
    if (!pattern) return null;
    const patternInfo = patterns?.find(p => formatPatternName(p.type) === pattern);
    const isBullish = patternInfo?.signal === 'BUY';
    const isBearish = patternInfo?.signal === 'SELL';

    return (
      <span className={`px-1.5 py-0.5 rounded text-xs font-medium flex items-center gap-1 ${
        isBullish ? 'bg-green-500/20 text-green-400' :
        isBearish ? 'bg-red-500/20 text-red-400' :
        'bg-blue-500/20 text-blue-400'
      }`}>
        <Flag className="w-2.5 h-2.5" />
        {pattern}
      </span>
    );
  };

  return (
    <div
      onClick={() => onSelect?.(item.symbol)}
      className={`grid grid-cols-[2fr_1fr_1fr_1fr_0.8fr_1.2fr_32px] gap-1 sm:gap-2 px-2 sm:px-4 py-3 hover:bg-slate-700/50 cursor-pointer transition-colors ${
        item.isActive ? 'bg-green-500/5' : ''
      }`}
    >
      {/* Symbol */}
      <div className="flex items-center gap-2 overflow-hidden">
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-1">
            <span className="font-semibold text-white truncate text-sm">{item.symbol}</span>
            {item.isActive && (
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse flex-shrink-0" title="Active Position"></span>
            )}
            {item.isBotDiscovered && (
              <span title="Bot Discovered" className="flex-shrink-0"><Sparkles className="w-3 h-3 text-purple-400" /></span>
            )}
          </div>
          {item.name && (
            <span className="text-xs text-slate-500 truncate hidden sm:block">{item.name}</span>
          )}
        </div>
      </div>

      {/* Price */}
      <div className="flex items-center justify-end">
        <span className="font-medium text-white text-xs sm:text-sm">${item.currentPrice.toFixed(2)}</span>
      </div>

      {/* Change - hidden on mobile */}
      <div className="hidden sm:flex items-center justify-end">
        <div className={`flex items-center gap-0.5 text-xs sm:text-sm ${item.changePct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {item.changePct >= 0 ? (
            <ArrowUpRight className="w-3 h-3" />
          ) : (
            <ArrowDownRight className="w-3 h-3" />
          )}
          <span className="font-medium">
            {item.changePct >= 0 ? '+' : ''}{item.changePct.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* AI Signal */}
      <div className="flex items-center justify-center">
        <span className={`px-1 sm:px-1.5 py-0.5 rounded text-xs font-medium ${getSignalColor(item.aiSignal)}`}>
          {item.aiSignal || 'N/A'}
        </span>
      </div>

      {/* Confidence - hidden on smaller screens */}
      <div className="hidden md:flex items-center justify-end">
        <span className={`text-xs font-medium ${getConfidenceColor(item.aiConfidence)}`}>
          {item.aiConfidence?.toFixed(0) || '--'}%
        </span>
      </div>

      {/* Pattern - Smart Carousel Feature - hidden on smaller screens */}
      <div className="hidden lg:flex items-center justify-center">
        {getPatternBadge(item.primaryPattern, item.detectedPatterns) || (
          <span className="text-xs text-slate-500">--</span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end">
        <Link
          to={item.symbol.includes('/') ? `/crypto` : `/stock/${item.symbol}`}
          onClick={(e) => e.stopPropagation()}
          className="p-1 hover:bg-slate-600 rounded transition-colors"
          title="View Details"
        >
          <BarChart3 className="w-4 h-4 text-slate-400" />
        </Link>
      </div>
    </div>
  );
}
