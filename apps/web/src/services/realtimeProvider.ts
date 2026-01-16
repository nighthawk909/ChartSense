/**
 * Real-Time Data Provider for TradingView Charts
 *
 * This service provides WebSocket-based real-time data for both stocks and crypto.
 * It uses Alpaca's WebSocket API for live tick data instead of REST polling.
 *
 * Key Features:
 * - True WebSocket streaming (no polling)
 * - Automatic reconnection with exponential backoff
 * - Symbol subscription management
 * - Cross-component data sharing via callbacks
 * - Support for both stocks and crypto symbols
 */

const ALPACA_WS_URL_STOCKS = 'wss://stream.data.alpaca.markets/v2/iex'
const ALPACA_WS_URL_CRYPTO = 'wss://stream.data.alpaca.markets/v1beta3/crypto/us'

type BarData = {
  time: number // Unix timestamp in seconds
  open: number
  high: number
  low: number
  close: number
  volume: number
}

type QuoteData = {
  symbol: string
  bidPrice: number
  askPrice: number
  bidSize: number
  askSize: number
  timestamp: number
}

type TradeData = {
  symbol: string
  price: number
  size: number
  timestamp: number
}

type SubscriptionCallback = (data: BarData | QuoteData | TradeData) => void

interface Subscription {
  symbol: string
  type: 'bar' | 'quote' | 'trade'
  callback: SubscriptionCallback
  id: string
}

export class RealTimeProvider {
  private stockWs: WebSocket | null = null
  private cryptoWs: WebSocket | null = null
  private subscriptions: Map<string, Subscription[]> = new Map()
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 10
  private reconnectDelay: number = 1000 // Start with 1 second
  private apiKey: string
  private secretKey: string
  private isAuthenticated: { stocks: boolean; crypto: boolean } = { stocks: false, crypto: false }
  private pendingSubscriptions: { stocks: string[]; crypto: string[] } = { stocks: [], crypto: [] }
  private onStatusChange: ((status: 'connected' | 'disconnected' | 'reconnecting' | 'error') => void) | null = null

  constructor(apiKey: string, secretKey: string) {
    this.apiKey = apiKey
    this.secretKey = secretKey
  }

  /**
   * Set status change callback
   */
  setStatusCallback(callback: (status: 'connected' | 'disconnected' | 'reconnecting' | 'error') => void) {
    this.onStatusChange = callback
  }

  /**
   * Connect to both stock and crypto WebSocket streams
   */
  async connect(): Promise<void> {
    await Promise.all([
      this.connectStocks(),
      this.connectCrypto(),
    ])
  }

  /**
   * Connect to stock data WebSocket
   */
  private async connectStocks(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.stockWs?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      this.stockWs = new WebSocket(ALPACA_WS_URL_STOCKS)

      this.stockWs.onopen = () => {
        console.log('[RealTimeProvider] Stock WebSocket connected')
        this.authenticate('stocks')
      }

      this.stockWs.onmessage = (event) => {
        this.handleMessage(event.data, 'stocks')
        if (this.isAuthenticated.stocks) {
          resolve()
        }
      }

      this.stockWs.onerror = (error) => {
        console.error('[RealTimeProvider] Stock WebSocket error:', error)
        this.onStatusChange?.('error')
        reject(error)
      }

      this.stockWs.onclose = () => {
        console.log('[RealTimeProvider] Stock WebSocket closed')
        this.isAuthenticated.stocks = false
        this.handleReconnect('stocks')
      }
    })
  }

  /**
   * Connect to crypto data WebSocket
   */
  private async connectCrypto(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.cryptoWs?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      this.cryptoWs = new WebSocket(ALPACA_WS_URL_CRYPTO)

      this.cryptoWs.onopen = () => {
        console.log('[RealTimeProvider] Crypto WebSocket connected')
        this.authenticate('crypto')
      }

      this.cryptoWs.onmessage = (event) => {
        this.handleMessage(event.data, 'crypto')
        if (this.isAuthenticated.crypto) {
          resolve()
        }
      }

      this.cryptoWs.onerror = (error) => {
        console.error('[RealTimeProvider] Crypto WebSocket error:', error)
        this.onStatusChange?.('error')
        reject(error)
      }

      this.cryptoWs.onclose = () => {
        console.log('[RealTimeProvider] Crypto WebSocket closed')
        this.isAuthenticated.crypto = false
        this.handleReconnect('crypto')
      }
    })
  }

  /**
   * Send authentication message
   */
  private authenticate(type: 'stocks' | 'crypto') {
    const ws = type === 'stocks' ? this.stockWs : this.cryptoWs
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    const authMessage = {
      action: 'auth',
      key: this.apiKey,
      secret: this.secretKey,
    }

    ws.send(JSON.stringify(authMessage))
    console.log(`[RealTimeProvider] Sent auth for ${type}`)
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(data: string, type: 'stocks' | 'crypto') {
    try {
      const messages = JSON.parse(data)

      for (const msg of Array.isArray(messages) ? messages : [messages]) {
        // Handle authentication response
        if (msg.T === 'success' && msg.msg === 'authenticated') {
          console.log(`[RealTimeProvider] ${type} authenticated successfully`)
          this.isAuthenticated[type] = true
          this.reconnectAttempts = 0
          this.reconnectDelay = 1000
          this.onStatusChange?.('connected')

          // Subscribe to any pending symbols
          const pending = type === 'stocks' ? this.pendingSubscriptions.stocks : this.pendingSubscriptions.crypto
          if (pending.length > 0) {
            this.subscribeToSymbols(pending, type)
            if (type === 'stocks') {
              this.pendingSubscriptions.stocks = []
            } else {
              this.pendingSubscriptions.crypto = []
            }
          }
          continue
        }

        // Handle authentication error
        if (msg.T === 'error') {
          console.error(`[RealTimeProvider] ${type} error:`, msg.msg)
          this.onStatusChange?.('error')
          continue
        }

        // Handle bar data (1-minute candles)
        if (msg.T === 'b') {
          const barData: BarData = {
            time: Math.floor(new Date(msg.t).getTime() / 1000),
            open: msg.o,
            high: msg.h,
            low: msg.l,
            close: msg.c,
            volume: msg.v,
          }
          this.notifySubscribers(msg.S, 'bar', barData)
        }

        // Handle quote data
        if (msg.T === 'q') {
          const quoteData: QuoteData = {
            symbol: msg.S,
            bidPrice: msg.bp,
            askPrice: msg.ap,
            bidSize: msg.bs,
            askSize: msg.as,
            timestamp: new Date(msg.t).getTime(),
          }
          this.notifySubscribers(msg.S, 'quote', quoteData)
        }

        // Handle trade data
        if (msg.T === 't') {
          const tradeData: TradeData = {
            symbol: msg.S,
            price: msg.p,
            size: msg.s,
            timestamp: new Date(msg.t).getTime(),
          }
          this.notifySubscribers(msg.S, 'trade', tradeData)
        }
      }
    } catch (error) {
      console.error('[RealTimeProvider] Error parsing message:', error)
    }
  }

  /**
   * Handle WebSocket reconnection with exponential backoff
   */
  private handleReconnect(type: 'stocks' | 'crypto') {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`[RealTimeProvider] Max reconnect attempts reached for ${type}`)
      this.onStatusChange?.('disconnected')
      return
    }

    this.reconnectAttempts++
    this.onStatusChange?.('reconnecting')

    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000)
    console.log(`[RealTimeProvider] Reconnecting ${type} in ${delay}ms (attempt ${this.reconnectAttempts})`)

    setTimeout(() => {
      if (type === 'stocks') {
        this.connectStocks().catch(console.error)
      } else {
        this.connectCrypto().catch(console.error)
      }
    }, delay)
  }

  /**
   * Subscribe to symbols for bar data
   */
  private subscribeToSymbols(symbols: string[], type: 'stocks' | 'crypto') {
    const ws = type === 'stocks' ? this.stockWs : this.cryptoWs
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn(`[RealTimeProvider] Cannot subscribe - ${type} WebSocket not open`)
      return
    }

    const subscribeMessage = {
      action: 'subscribe',
      bars: symbols,
      quotes: symbols,
      trades: symbols,
    }

    ws.send(JSON.stringify(subscribeMessage))
    console.log(`[RealTimeProvider] Subscribed to ${type}:`, symbols)
  }

  /**
   * Unsubscribe from symbols
   */
  private unsubscribeFromSymbols(symbols: string[], type: 'stocks' | 'crypto') {
    const ws = type === 'stocks' ? this.stockWs : this.cryptoWs
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    const unsubscribeMessage = {
      action: 'unsubscribe',
      bars: symbols,
      quotes: symbols,
      trades: symbols,
    }

    ws.send(JSON.stringify(unsubscribeMessage))
    console.log(`[RealTimeProvider] Unsubscribed from ${type}:`, symbols)
  }

  /**
   * Notify all subscribers for a symbol
   */
  private notifySubscribers(symbol: string, dataType: 'bar' | 'quote' | 'trade', data: BarData | QuoteData | TradeData) {
    const subs = this.subscriptions.get(symbol) || []
    for (const sub of subs) {
      if (sub.type === dataType) {
        try {
          sub.callback(data)
        } catch (error) {
          console.error(`[RealTimeProvider] Error in subscriber callback for ${symbol}:`, error)
        }
      }
    }
  }

  /**
   * Determine if a symbol is crypto
   */
  private isCryptoSymbol(symbol: string): boolean {
    return symbol.includes('/') || symbol.endsWith('USD')
  }

  /**
   * Subscribe to real-time bar updates for a symbol
   * Used by TradingView's subscribeBars
   */
  subscribeBars(
    symbol: string,
    callback: (bar: BarData) => void
  ): string {
    const subscriptionId = `bar_${symbol}_${Date.now()}`
    const isCrypto = this.isCryptoSymbol(symbol)
    const type = isCrypto ? 'crypto' : 'stocks'

    const subscription: Subscription = {
      symbol,
      type: 'bar',
      callback: callback as SubscriptionCallback,
      id: subscriptionId,
    }

    // Add to subscriptions
    const existing = this.subscriptions.get(symbol) || []
    existing.push(subscription)
    this.subscriptions.set(symbol, existing)

    // Subscribe via WebSocket if authenticated, otherwise queue
    if (this.isAuthenticated[type]) {
      this.subscribeToSymbols([symbol], type)
    } else {
      if (isCrypto) {
        this.pendingSubscriptions.crypto.push(symbol)
      } else {
        this.pendingSubscriptions.stocks.push(symbol)
      }
    }

    console.log(`[RealTimeProvider] Added bar subscription for ${symbol} (ID: ${subscriptionId})`)
    return subscriptionId
  }

  /**
   * Unsubscribe from real-time updates
   */
  unsubscribeBars(subscriptionId: string): void {
    // Find and remove the subscription
    for (const [symbol, subs] of this.subscriptions.entries()) {
      const index = subs.findIndex(s => s.id === subscriptionId)
      if (index !== -1) {
        subs.splice(index, 1)

        // If no more subscriptions for this symbol, unsubscribe from WebSocket
        if (subs.length === 0) {
          const isCrypto = this.isCryptoSymbol(symbol)
          this.unsubscribeFromSymbols([symbol], isCrypto ? 'crypto' : 'stocks')
          this.subscriptions.delete(symbol)
        } else {
          this.subscriptions.set(symbol, subs)
        }

        console.log(`[RealTimeProvider] Removed subscription ${subscriptionId}`)
        return
      }
    }
  }

  /**
   * Subscribe to real-time quotes for a symbol
   */
  subscribeQuotes(
    symbol: string,
    callback: (quote: QuoteData) => void
  ): string {
    const subscriptionId = `quote_${symbol}_${Date.now()}`
    const isCrypto = this.isCryptoSymbol(symbol)
    const type = isCrypto ? 'crypto' : 'stocks'

    const subscription: Subscription = {
      symbol,
      type: 'quote',
      callback: callback as SubscriptionCallback,
      id: subscriptionId,
    }

    const existing = this.subscriptions.get(symbol) || []
    existing.push(subscription)
    this.subscriptions.set(symbol, existing)

    if (this.isAuthenticated[type]) {
      this.subscribeToSymbols([symbol], type)
    } else {
      if (isCrypto) {
        this.pendingSubscriptions.crypto.push(symbol)
      } else {
        this.pendingSubscriptions.stocks.push(symbol)
      }
    }

    return subscriptionId
  }

  /**
   * Force refresh - clear local cache and request fresh data
   * This is a client-side operation that clears any cached state
   */
  forceRefresh(symbol: string): void {
    console.log(`[RealTimeProvider] Force refresh requested for ${symbol}`)
    // Re-subscribe to get fresh data stream
    const isCrypto = this.isCryptoSymbol(symbol)
    const type = isCrypto ? 'crypto' : 'stocks'

    // Unsubscribe and resubscribe to force fresh connection
    this.unsubscribeFromSymbols([symbol], type)
    setTimeout(() => {
      this.subscribeToSymbols([symbol], type)
    }, 100)
  }

  /**
   * Disconnect all WebSocket connections
   */
  disconnect(): void {
    if (this.stockWs) {
      this.stockWs.close()
      this.stockWs = null
    }
    if (this.cryptoWs) {
      this.cryptoWs.close()
      this.cryptoWs = null
    }
    this.subscriptions.clear()
    this.isAuthenticated = { stocks: false, crypto: false }
    this.onStatusChange?.('disconnected')
    console.log('[RealTimeProvider] Disconnected all WebSocket connections')
  }

  /**
   * Get connection status
   */
  getStatus(): { stocks: boolean; crypto: boolean } {
    return {
      stocks: this.stockWs?.readyState === WebSocket.OPEN && this.isAuthenticated.stocks,
      crypto: this.cryptoWs?.readyState === WebSocket.OPEN && this.isAuthenticated.crypto,
    }
  }
}

// Singleton instance - will be initialized with API keys from environment
let _instance: RealTimeProvider | null = null

export function getRealTimeProvider(): RealTimeProvider | null {
  return _instance
}

export function initRealTimeProvider(apiKey: string, secretKey: string): RealTimeProvider {
  if (_instance) {
    _instance.disconnect()
  }
  _instance = new RealTimeProvider(apiKey, secretKey)
  return _instance
}

export type { BarData, QuoteData, TradeData }
