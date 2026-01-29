/**
 * Trading Bot API Service
 * Handles all API calls related to the trading bot
 *
 * Features:
 * - Standardized error handling with ApiResponse<T> wrapper
 * - Automatic retry for transient failures (network, 5xx)
 * - Configurable timeout (default 10s)
 * - Error type detection helpers
 */
import axios, { AxiosError, AxiosRequestConfig } from 'axios';
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
import type {
  ApiResponse,
  ApiError,
  ApiErrorCode,
  ApiCallOptions,
} from '../types/api';
import { DEFAULT_API_OPTIONS } from '../types/api';

// Base API URL - uses Vite proxy in development, full URL in production
const API_URL = import.meta.env.VITE_API_URL || '';
const API_BASE = API_URL ? `${API_URL}/api` : '/api';

// Create axios instance with defaults
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: DEFAULT_API_OPTIONS.timeout,
});

// ============== Error Handling Utilities ==============

/**
 * Map HTTP status code to ApiErrorCode
 */
function getErrorCode(status?: number, isTimeout?: boolean): ApiErrorCode {
  if (isTimeout) return 'TIMEOUT';
  if (!status) return 'NETWORK_ERROR';

  if (status === 401) return 'AUTH_ERROR';
  if (status === 403) return 'FORBIDDEN';
  if (status === 404) return 'NOT_FOUND';
  if (status === 429) return 'RATE_LIMIT';
  if (status >= 400 && status < 500) return 'VALIDATION_ERROR';
  if (status >= 500) return 'SERVER_ERROR';

  return 'UNKNOWN';
}

/**
 * Determine if an error is retryable
 */
function isRetryableError(code: ApiErrorCode): boolean {
  return ['NETWORK_ERROR', 'TIMEOUT', 'SERVER_ERROR', 'RATE_LIMIT'].includes(code);
}

/**
 * Parse axios error into structured ApiError
 */
function parseAxiosError(error: AxiosError): ApiError {
  const isTimeout = error.code === 'ECONNABORTED' || error.message.includes('timeout');
  const status = error.response?.status;
  const code = getErrorCode(status, isTimeout);

  // Extract message from response or use default
  let message = 'An unexpected error occurred';
  if (error.response?.data) {
    const data = error.response.data as Record<string, unknown>;
    message = (data.detail as string) || (data.message as string) || message;
  } else if (isTimeout) {
    message = 'Request timed out. Please try again.';
  } else if (!error.response) {
    message = 'Unable to connect to server. Please check your connection.';
  }

  return {
    code,
    message,
    statusCode: status,
    details: error.response?.data as Record<string, unknown> | undefined,
    retryable: isRetryableError(code),
  };
}

/**
 * Sleep utility for retry delay
 */
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Wrap an API call with standardized error handling and retry logic
 *
 * @param apiCall - The async function to execute
 * @param options - Configuration options
 * @returns ApiResponse with success/data or error
 */
export async function wrapApiCall<T>(
  apiCall: () => Promise<T>,
  options: ApiCallOptions = {}
): Promise<ApiResponse<T>> {
  const opts = { ...DEFAULT_API_OPTIONS, ...options };
  let lastError: ApiError | undefined;

  for (let attempt = 0; attempt <= opts.maxRetries; attempt++) {
    try {
      const data = await apiCall();
      return { success: true, data };
    } catch (err) {
      const error = err as AxiosError;
      lastError = parseAxiosError(error);

      // Only retry if enabled, error is retryable, and we have attempts left
      const shouldRetry = opts.retry && lastError.retryable && attempt < opts.maxRetries;

      if (shouldRetry) {
        // Exponential backoff for rate limits
        const delay = lastError.code === 'RATE_LIMIT'
          ? opts.retryDelay * Math.pow(2, attempt)
          : opts.retryDelay;
        await sleep(delay);
        continue;
      }

      break;
    }
  }

  return { success: false, error: lastError };
}

// ============== Error Type Checkers ==============

/**
 * Check if error is a network connectivity error
 */
export function isNetworkError(error?: ApiError): boolean {
  return error?.code === 'NETWORK_ERROR' || error?.code === 'TIMEOUT';
}

/**
 * Check if error is an authentication error (401)
 */
export function isAuthError(error?: ApiError): boolean {
  return error?.code === 'AUTH_ERROR';
}

/**
 * Check if error is a rate limit error (429)
 */
export function isRateLimitError(error?: ApiError): boolean {
  return error?.code === 'RATE_LIMIT';
}

/**
 * Check if error is a server error (5xx)
 */
export function isServerError(error?: ApiError): boolean {
  return error?.code === 'SERVER_ERROR';
}

/**
 * Check if error is a validation error (400)
 */
export function isValidationError(error?: ApiError): boolean {
  return error?.code === 'VALIDATION_ERROR';
}

/**
 * Check if error is retryable
 */
export function isRetryable(error?: ApiError): boolean {
  return error?.retryable ?? false;
}

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

// ============== Wrapped APIs (with error handling) ==============
// These APIs return ApiResponse<T> for consistent error handling

/**
 * Bot control API with standardized error handling
 */
export const safeBotApi = {
  getStatus: (options?: ApiCallOptions) =>
    wrapApiCall(() => botApi.getStatus(), options),

  start: (request?: BotStartRequest, options?: ApiCallOptions) =>
    wrapApiCall(() => botApi.start(request), options),

  stop: (options?: ApiCallOptions) =>
    wrapApiCall(() => botApi.stop(), options),

  pause: (options?: ApiCallOptions) =>
    wrapApiCall(() => botApi.pause(), options),

  resume: (options?: ApiCallOptions) =>
    wrapApiCall(() => botApi.resume(), options),

  getHealth: (options?: ApiCallOptions) =>
    wrapApiCall(() => botApi.getHealth(), options),
};

/**
 * Positions API with standardized error handling
 */
export const safePositionsApi = {
  getAccount: (options?: ApiCallOptions) =>
    wrapApiCall(() => positionsApi.getAccount(), options),

  getPositions: (options?: ApiCallOptions) =>
    wrapApiCall(() => positionsApi.getPositions(), options),

  getPosition: (symbol: string, options?: ApiCallOptions) =>
    wrapApiCall(() => positionsApi.getPosition(symbol), options),

  closePosition: (symbol: string, quantity?: number, options?: ApiCallOptions) =>
    wrapApiCall(() => positionsApi.closePosition(symbol, quantity), options),

  closeAllPositions: (options?: ApiCallOptions) =>
    wrapApiCall(() => positionsApi.closeAllPositions(), options),
};

/**
 * Performance API with standardized error handling
 */
export const safePerformanceApi = {
  getSummary: (periodDays?: number, options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.getSummary(periodDays), options),

  getMetrics: (periodDays?: number, options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.getMetrics(periodDays), options),

  getEquityCurve: (periodDays?: number, options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.getEquityCurve(periodDays), options),

  getTrades: (page?: number, pageSize?: number, options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.getTrades(page, pageSize), options),

  getTrade: (tradeId: number, options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.getTrade(tradeId), options),

  getOptimizationHistory: (limit?: number, options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.getOptimizationHistory(limit), options),

  triggerOptimization: (options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.triggerOptimization(), options),

  getTradeAnalysis: (tradeId: number, options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.getTradeAnalysis(tradeId), options),

  analyzeTradeAgain: (tradeId: number, options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.analyzeTradeAgain(tradeId), options),

  getDailySummary: (date?: string, options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.getDailySummary(date), options),

  getWeeklyReport: (options?: ApiCallOptions) =>
    wrapApiCall(() => performanceApi.getWeeklyReport(), options),
};

/**
 * Settings API with standardized error handling
 */
export const safeSettingsApi = {
  getSettings: (options?: ApiCallOptions) =>
    wrapApiCall(() => settingsApi.getSettings(), options),

  updateSettings: (settings: BotSettings, options?: ApiCallOptions) =>
    wrapApiCall(() => settingsApi.updateSettings(settings), options),

  resetSettings: (options?: ApiCallOptions) =>
    wrapApiCall(() => settingsApi.resetSettings(), options),

  getPresets: (options?: ApiCallOptions) =>
    wrapApiCall(() => settingsApi.getPresets(), options),

  applyPreset: (presetName: string, options?: ApiCallOptions) =>
    wrapApiCall(() => settingsApi.applyPreset(presetName), options),
};

/**
 * Combined safe trading API
 */
export const safeTradingApi = {
  bot: safeBotApi,
  positions: safePositionsApi,
  performance: safePerformanceApi,
  settings: safeSettingsApi,
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

// Re-export types for convenience
export type { ApiResponse, ApiError, ApiErrorCode, ApiCallOptions } from '../types/api';

export default tradingApi;
