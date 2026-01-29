/**
 * Standardized API Response Types
 * Provides consistent error handling across all API calls
 */

/**
 * Error codes for categorizing API failures
 */
export type ApiErrorCode =
  | 'NETWORK_ERROR'      // Network unreachable, timeout, CORS
  | 'AUTH_ERROR'         // 401 Unauthorized
  | 'FORBIDDEN'          // 403 Forbidden
  | 'NOT_FOUND'          // 404 Not Found
  | 'RATE_LIMIT'         // 429 Too Many Requests
  | 'VALIDATION_ERROR'   // 400 Bad Request / validation failed
  | 'SERVER_ERROR'       // 5xx errors
  | 'TIMEOUT'            // Request timeout
  | 'UNKNOWN';           // Unexpected error

/**
 * Structured error object
 */
export interface ApiError {
  code: ApiErrorCode;
  message: string;
  details?: Record<string, unknown>;
  statusCode?: number;
  retryable: boolean;
}

/**
 * Standardized API response wrapper
 * All API calls return this format for consistent handling
 */
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
}

/**
 * Options for API call wrapper
 */
export interface ApiCallOptions {
  /** Request timeout in milliseconds (default: 10000) */
  timeout?: number;
  /** Whether to retry on transient failures (default: true) */
  retry?: boolean;
  /** Maximum retry attempts (default: 1) */
  maxRetries?: number;
  /** Delay between retries in ms (default: 1000) */
  retryDelay?: number;
}

/**
 * Default options for API calls
 */
export const DEFAULT_API_OPTIONS: Required<ApiCallOptions> = {
  timeout: 10000,
  retry: true,
  maxRetries: 1,
  retryDelay: 1000,
};
