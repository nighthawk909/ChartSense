/**
 * useRealTimeData - React hook for real-time chart data
 *
 * This hook provides WebSocket-based real-time data for TradingView charts.
 * It handles connection management, subscription lifecycle, and force refresh.
 *
 * Usage:
 *   const { latestBar, latestQuote, status, forceRefresh } = useRealTimeData(symbol)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  RealTimeProvider,
  BarData,
  QuoteData,
  getRealTimeProvider,
  initRealTimeProvider,
} from '../services/realtimeProvider'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error'

interface UseRealTimeDataResult {
  latestBar: BarData | null
  latestQuote: QuoteData | null
  status: ConnectionStatus
  error: string | null
  forceRefresh: () => void
  isConnected: boolean
}

export function useRealTimeData(symbol: string): UseRealTimeDataResult {
  const [latestBar, setLatestBar] = useState<BarData | null>(null)
  const [latestQuote, setLatestQuote] = useState<QuoteData | null>(null)
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [error, setError] = useState<string | null>(null)

  const providerRef = useRef<RealTimeProvider | null>(null)
  const barSubscriptionRef = useRef<string | null>(null)
  const quoteSubscriptionRef = useRef<string | null>(null)

  // Initialize provider on mount
  useEffect(() => {
    const initProvider = async () => {
      try {
        // Get API keys from backend
        const response = await fetch(`${API_URL}/api/settings`)
        const settings = await response.json()

        // Check if we have API keys configured
        if (!settings.alpaca_api_key || !settings.alpaca_secret_key) {
          console.warn('[useRealTimeData] Alpaca API keys not configured, using REST fallback')
          setStatus('disconnected')
          return
        }

        // Initialize provider
        let provider = getRealTimeProvider()
        if (!provider) {
          provider = initRealTimeProvider(settings.alpaca_api_key, settings.alpaca_secret_key)
        }

        provider.setStatusCallback((newStatus) => {
          setStatus(newStatus)
          if (newStatus === 'error') {
            setError('WebSocket connection error')
          } else {
            setError(null)
          }
        })

        await provider.connect()
        providerRef.current = provider
        setStatus('connected')
      } catch (err) {
        console.error('[useRealTimeData] Failed to initialize provider:', err)
        setError(err instanceof Error ? err.message : 'Failed to connect')
        setStatus('error')
      }
    }

    initProvider()

    return () => {
      // Cleanup subscriptions but don't disconnect the shared provider
      if (barSubscriptionRef.current && providerRef.current) {
        providerRef.current.unsubscribeBars(barSubscriptionRef.current)
      }
      if (quoteSubscriptionRef.current && providerRef.current) {
        providerRef.current.unsubscribeBars(quoteSubscriptionRef.current)
      }
    }
  }, [])

  // Subscribe to symbol updates
  useEffect(() => {
    if (!providerRef.current || status !== 'connected' || !symbol) return

    // Cleanup previous subscriptions
    if (barSubscriptionRef.current) {
      providerRef.current.unsubscribeBars(barSubscriptionRef.current)
    }
    if (quoteSubscriptionRef.current) {
      providerRef.current.unsubscribeBars(quoteSubscriptionRef.current)
    }

    // Subscribe to bar updates
    barSubscriptionRef.current = providerRef.current.subscribeBars(symbol, (bar) => {
      setLatestBar(bar as BarData)
    })

    // Subscribe to quote updates
    quoteSubscriptionRef.current = providerRef.current.subscribeQuotes(symbol, (quote) => {
      setLatestQuote(quote as QuoteData)
    })

    return () => {
      if (barSubscriptionRef.current && providerRef.current) {
        providerRef.current.unsubscribeBars(barSubscriptionRef.current)
        barSubscriptionRef.current = null
      }
      if (quoteSubscriptionRef.current && providerRef.current) {
        providerRef.current.unsubscribeBars(quoteSubscriptionRef.current)
        quoteSubscriptionRef.current = null
      }
    }
  }, [symbol, status])

  // Force refresh handler
  const forceRefresh = useCallback(() => {
    if (providerRef.current && symbol) {
      providerRef.current.forceRefresh(symbol)
      // Also clear local state to show loading
      setLatestBar(null)
      setLatestQuote(null)
    }
  }, [symbol])

  return {
    latestBar,
    latestQuote,
    status,
    error,
    forceRefresh,
    isConnected: status === 'connected',
  }
}

/**
 * useRealTimeConnection - Hook just for connection status
 * Useful for showing global connection indicator
 */
export function useRealTimeConnection(): {
  isConnected: boolean
  status: ConnectionStatus
  stocks: boolean
  crypto: boolean
} {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [connectionStatus, setConnectionStatus] = useState({ stocks: false, crypto: false })

  useEffect(() => {
    const provider = getRealTimeProvider()
    if (provider) {
      provider.setStatusCallback((newStatus) => {
        setStatus(newStatus)
        setConnectionStatus(provider.getStatus())
      })
      setConnectionStatus(provider.getStatus())
      setStatus(provider.getStatus().stocks || provider.getStatus().crypto ? 'connected' : 'disconnected')
    }
  }, [])

  return {
    isConnected: status === 'connected',
    status,
    stocks: connectionStatus.stocks,
    crypto: connectionStatus.crypto,
  }
}

export type { ConnectionStatus, BarData, QuoteData }
