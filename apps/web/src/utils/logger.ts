/**
 * Logger utility for ChartSense
 * Provides conditional logging based on environment
 * Logs are only displayed in development mode
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LoggerOptions {
  prefix?: string;
  showTimestamp?: boolean;
}

/**
 * Creates a namespaced logger with optional prefix
 * Usage:
 *   const logger = createLogger('TradingBot');
 *   logger.info('Bot started');
 *   // Output: [TradingBot] Bot started
 */
function createLogger(namespace: string, options: LoggerOptions = {}) {
  const { showTimestamp = false } = options;

  const formatMessage = (level: LogLevel, ...args: unknown[]): unknown[] => {
    const prefix = `[${namespace}]`;
    const timestamp = showTimestamp ? `[${new Date().toISOString()}]` : '';
    const levelTag = level === 'debug' ? '[DEBUG]' : '';

    const prefixParts = [prefix, timestamp, levelTag].filter(Boolean).join(' ');

    // If first argument is a string, prepend the prefix
    if (typeof args[0] === 'string') {
      return [`${prefixParts} ${args[0]}`, ...args.slice(1)];
    }
    return [prefixParts, ...args];
  };

  const shouldLog = (): boolean => {
    // Only log in development mode
    // import.meta.env.DEV is true during `npm run dev`
    // and false during production builds
    return import.meta.env.DEV;
  };

  return {
    /**
     * Debug level - for verbose diagnostic information
     * Only shown in development mode
     */
    debug: (...args: unknown[]): void => {
      if (shouldLog()) {
        console.log(...formatMessage('debug', ...args));
      }
    },

    /**
     * Info level - for general information
     * Only shown in development mode
     */
    info: (...args: unknown[]): void => {
      if (shouldLog()) {
        console.log(...formatMessage('info', ...args));
      }
    },

    /**
     * Warn level - for warnings
     * Only shown in development mode
     */
    warn: (...args: unknown[]): void => {
      if (shouldLog()) {
        console.warn(...formatMessage('warn', ...args));
      }
    },

    /**
     * Error level - for errors
     * Always shown (errors are important even in production)
     */
    error: (...args: unknown[]): void => {
      // Errors are always logged, even in production
      console.error(...formatMessage('error', ...args));
    },

    /**
     * Group - creates a collapsible group in console
     * Only shown in development mode
     */
    group: (label: string): void => {
      if (shouldLog()) {
        console.group(`[${namespace}] ${label}`);
      }
    },

    /**
     * GroupEnd - ends the current group
     * Only shown in development mode
     */
    groupEnd: (): void => {
      if (shouldLog()) {
        console.groupEnd();
      }
    },

    /**
     * Table - displays tabular data
     * Only shown in development mode
     */
    table: (data: unknown): void => {
      if (shouldLog()) {
        console.log(`[${namespace}]`);
        console.table(data);
      }
    },

    /**
     * Time - starts a timer with the given label
     * Only shown in development mode
     */
    time: (label: string): void => {
      if (shouldLog()) {
        console.time(`[${namespace}] ${label}`);
      }
    },

    /**
     * TimeEnd - ends a timer and logs the duration
     * Only shown in development mode
     */
    timeEnd: (label: string): void => {
      if (shouldLog()) {
        console.timeEnd(`[${namespace}] ${label}`);
      }
    },
  };
}

// Pre-configured loggers for common use cases
export const tradingBotLogger = createLogger('TradingBot');
export const chartLogger = createLogger('Chart');
export const apiLogger = createLogger('API');
export const wsLogger = createLogger('WebSocket');

// Export the factory function for custom loggers
export { createLogger };

// Default export for convenience
export default createLogger;
