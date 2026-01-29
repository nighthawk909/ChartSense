/**
 * Backtest API Service
 * Handles all API calls related to backtesting
 */
import axios from 'axios';
import type {
  BacktestRequest,
  BacktestResult,
  StrategiesResponse,
} from '../types/backtest';

// Base API URL
const API_URL = import.meta.env.VITE_API_URL || '';
const API_BASE = API_URL ? `${API_URL}/api` : '/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes - backtests can take time
});

export const backtestApi = {
  /**
   * Run a backtest with the specified configuration
   */
  runBacktest: async (request: BacktestRequest): Promise<BacktestResult> => {
    const response = await api.post<BacktestResult>('/advanced/backtest/run', request);
    return response.data;
  },

  /**
   * Get list of available strategies
   */
  getStrategies: async (): Promise<StrategiesResponse> => {
    const response = await api.get<StrategiesResponse>('/advanced/backtest/strategies');
    return response.data;
  },

  /**
   * Health check for backtest service
   */
  healthCheck: async (): Promise<{ status: string; service: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default backtestApi;
