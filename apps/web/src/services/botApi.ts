/**
 * Trading Bot API Service
 * Handles all API calls related to the trading bot
 */
import axios from 'axios';
import type {
  BotStatus,
  BotActionResponse,
  BotStartRequest,
  AccountSummary,
  Position,
  PositionsList,
  ClosePositionResponse,
  Trade,
  TradeHistory,
  PerformanceSummary,
  PerformanceMetrics,
  EquityCurve,
  BotSettings,
  BotSettingsResponse,
  SettingsPreset,
  OptimizationHistory,
  BotHealth,
  TradeAnalysis,
  DailySummary,
  WeeklyReport,
} from '../types/bot';

// Base API URL - uses Vite proxy in development
const API_BASE = '/api';

// Create axios instance with defaults
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============== Bot Control ==============

export const botApi = {
  /**
   * Get current bot status
   */
  getStatus: async (): Promise<BotStatus> => {
    const response = await api.get<BotStatus>('/bot/status');
    return response.data;
  },

  /**
   * Start the trading bot
   */
  start: async (request?: BotStartRequest): Promise<BotActionResponse> => {
    const response = await api.post<BotActionResponse>('/bot/start', request);
    return response.data;
  },

  /**
   * Stop the trading bot
   */
  stop: async (): Promise<BotActionResponse> => {
    const response = await api.post<BotActionResponse>('/bot/stop');
    return response.data;
  },

  /**
   * Pause the trading bot
   */
  pause: async (): Promise<BotActionResponse> => {
    const response = await api.post<BotActionResponse>('/bot/pause');
    return response.data;
  },

  /**
   * Resume the trading bot from paused state
   */
  resume: async (): Promise<BotActionResponse> => {
    const response = await api.post<BotActionResponse>('/bot/resume');
    return response.data;
  },

  /**
   * Check bot health and connectivity
   */
  getHealth: async (): Promise<BotHealth> => {
    const response = await api.get<BotHealth>('/bot/health');
    return response.data;
  },
};

// ============== Account & Positions ==============

export const positionsApi = {
  /**
   * Get account summary
   */
  getAccount: async (): Promise<AccountSummary> => {
    const response = await api.get<AccountSummary>('/positions/account');
    return response.data;
  },

  /**
   * Get all current positions
   */
  getPositions: async (): Promise<PositionsList> => {
    const response = await api.get<PositionsList>('/positions/current');
    return response.data;
  },

  /**
   * Get a specific position
   */
  getPosition: async (symbol: string): Promise<Position> => {
    const response = await api.get<Position>(`/positions/${symbol}`);
    return response.data;
  },

  /**
   * Close a position
   */
  closePosition: async (symbol: string, quantity?: number): Promise<ClosePositionResponse> => {
    const response = await api.post<ClosePositionResponse>(
      `/positions/close/${symbol}`,
      null,
      { params: { quantity } }
    );
    return response.data;
  },

  /**
   * Close all positions
   */
  closeAllPositions: async (): Promise<{ success: boolean; message: string }> => {
    const response = await api.post('/positions/close-all');
    return response.data;
  },
};

// ============== Performance ==============

export const performanceApi = {
  /**
   * Get quick performance summary
   */
  getSummary: async (periodDays: number = 30): Promise<PerformanceSummary> => {
    const response = await api.get<PerformanceSummary>('/performance/summary', {
      params: { period_days: periodDays },
    });
    return response.data;
  },

  /**
   * Get detailed performance metrics
   */
  getMetrics: async (periodDays: number = 30): Promise<PerformanceMetrics> => {
    const response = await api.get<PerformanceMetrics>('/performance/metrics', {
      params: { period_days: periodDays },
    });
    return response.data;
  },

  /**
   * Get equity curve data for charting
   */
  getEquityCurve: async (periodDays: number = 30): Promise<EquityCurve> => {
    const response = await api.get<EquityCurve>('/performance/equity-curve', {
      params: { period_days: periodDays },
    });
    return response.data;
  },

  /**
   * Get paginated trade history
   */
  getTrades: async (page: number = 1, pageSize: number = 20): Promise<TradeHistory> => {
    const response = await api.get<TradeHistory>('/performance/trades', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  /**
   * Get a specific trade by ID
   */
  getTrade: async (tradeId: number): Promise<Trade> => {
    const response = await api.get<Trade>(`/performance/trades/${tradeId}`);
    return response.data;
  },

  /**
   * Get optimization history
   */
  getOptimizationHistory: async (limit: number = 20): Promise<OptimizationHistory> => {
    const response = await api.get<OptimizationHistory>('/performance/optimization-history', {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Trigger manual optimization
   */
  triggerOptimization: async (): Promise<{
    suggestions: Array<{
      parameter: string;
      current: number;
      suggested: number;
      reason: string;
    }>;
    applied: string[];
    message: string;
  }> => {
    const response = await api.post('/performance/optimize');
    return response.data;
  },

  /**
   * Get post-mortem analysis for a trade
   */
  getTradeAnalysis: async (tradeId: number): Promise<TradeAnalysis> => {
    const response = await api.get<TradeAnalysis>(`/performance/trades/${tradeId}/analysis`);
    return response.data;
  },

  /**
   * Force re-analysis of a trade
   */
  analyzeTradeAgain: async (tradeId: number): Promise<TradeAnalysis> => {
    const response = await api.post<TradeAnalysis>(`/performance/trades/${tradeId}/analyze`);
    return response.data;
  },

  /**
   * Get daily trading summary
   */
  getDailySummary: async (date?: string): Promise<DailySummary> => {
    const response = await api.get<DailySummary>('/performance/daily-summary', {
      params: date ? { date } : {},
    });
    return response.data;
  },

  /**
   * Get weekly performance report
   */
  getWeeklyReport: async (): Promise<WeeklyReport> => {
    const response = await api.get<WeeklyReport>('/performance/weekly-report');
    return response.data;
  },
};

// ============== Settings ==============

export const settingsApi = {
  /**
   * Get current bot settings
   */
  getSettings: async (): Promise<BotSettingsResponse> => {
    const response = await api.get<BotSettingsResponse>('/settings/');
    return response.data;
  },

  /**
   * Update bot settings
   */
  updateSettings: async (settings: BotSettings): Promise<BotSettingsResponse> => {
    const response = await api.put<BotSettingsResponse>('/settings/', {
      settings,
    });
    return response.data;
  },

  /**
   * Reset settings to defaults
   */
  resetSettings: async (): Promise<{ success: boolean; message: string }> => {
    const response = await api.post('/settings/reset');
    return response.data;
  },

  /**
   * Get available presets
   */
  getPresets: async (): Promise<{ presets: SettingsPreset[] }> => {
    const response = await api.get('/settings/presets');
    return response.data;
  },

  /**
   * Apply a preset
   */
  applyPreset: async (presetName: string): Promise<{
    success: boolean;
    message: string;
    settings: Partial<BotSettings>;
  }> => {
    const response = await api.post(`/settings/presets/${presetName}`);
    return response.data;
  },
};

// ============== Utility Functions ==============

/**
 * Format currency value
 */
export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

/**
 * Format percentage value
 */
export const formatPercent = (value: number): string => {
  const formatted = value.toFixed(2);
  return value >= 0 ? `+${formatted}%` : `${formatted}%`;
};

/**
 * Format uptime in human-readable format
 */
export const formatUptime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
};

/**
 * Get status color class based on state
 */
export const getStateColor = (state: string): string => {
  switch (state) {
    case 'RUNNING':
      return 'text-green-500';
    case 'PAUSED':
      return 'text-yellow-500';
    case 'STOPPED':
      return 'text-slate-400';
    case 'ERROR':
      return 'text-red-500';
    default:
      return 'text-slate-400';
  }
};

/**
 * Get P&L color class
 */
export const getPnLColor = (value: number): string => {
  if (value > 0) return 'text-green-500';
  if (value < 0) return 'text-red-500';
  return 'text-slate-400';
};

// Export all APIs as a single object
export const tradingApi = {
  bot: botApi,
  positions: positionsApi,
  performance: performanceApi,
  settings: settingsApi,
};

export default tradingApi;
