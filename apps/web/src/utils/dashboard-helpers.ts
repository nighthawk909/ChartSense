/**
 * Dashboard helper functions
 */

/**
 * Get human-readable name for a stock or crypto symbol
 */
export function getSymbolName(symbol: string): string {
  // Common crypto symbols
  if (symbol.endsWith('USD') || symbol.includes('/')) {
    const base = symbol.replace('USD', '').replace('/USD', '').replace('/USDT', '')
    const cryptoNames: Record<string, string> = {
      'BTC': 'Bitcoin',
      'ETH': 'Ethereum',
      'SOL': 'Solana',
      'DOGE': 'Dogecoin',
      'ADA': 'Cardano',
      'XRP': 'Ripple',
      'DOT': 'Polkadot',
      'AVAX': 'Avalanche',
      'LINK': 'Chainlink',
      'MATIC': 'Polygon',
      'LTC': 'Litecoin',
      'BCH': 'Bitcoin Cash',
    }
    return cryptoNames[base] || `${base} (Crypto)`
  }
  // Common stock symbols
  const stockNames: Record<string, string> = {
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft Corp.',
    'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.',
    'NVDA': 'NVIDIA Corp.',
    'META': 'Meta Platforms',
    'TSLA': 'Tesla Inc.',
    'JPM': 'JPMorgan Chase',
    'V': 'Visa Inc.',
    'JNJ': 'Johnson & Johnson',
    'WMT': 'Walmart Inc.',
    'PG': 'Procter & Gamble',
  }
  return stockNames[symbol] || symbol
}

/**
 * Get CSS color class for indicator signal status
 */
export function getStatusColor(signal?: string): string {
  if (!signal) return 'text-slate-400'
  const lowerSignal = signal.toLowerCase()
  if (lowerSignal.includes('bullish') || lowerSignal.includes('oversold') || lowerSignal.includes('above')) {
    return 'text-green-500'
  }
  if (lowerSignal.includes('bearish') || lowerSignal.includes('overbought') || lowerSignal.includes('below')) {
    return 'text-red-500'
  }
  return 'text-yellow-500'
}
