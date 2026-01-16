/**
 * Crypto Selector Component
 * A toggle grid for selecting which cryptocurrencies to scan/trade
 */
import { Check } from 'lucide-react';

// Available cryptos on Alpaca - these are the ones we support
export const AVAILABLE_CRYPTOS = [
  { symbol: 'BTC/USD', name: 'Bitcoin', icon: '₿' },
  { symbol: 'ETH/USD', name: 'Ethereum', icon: 'Ξ' },
  { symbol: 'SOL/USD', name: 'Solana', icon: '◎' },
  { symbol: 'DOGE/USD', name: 'Dogecoin', icon: 'Ð' },
  { symbol: 'ADA/USD', name: 'Cardano', icon: '₳' },
  { symbol: 'XRP/USD', name: 'Ripple', icon: '✕' },
  { symbol: 'AVAX/USD', name: 'Avalanche', icon: 'A' },
  { symbol: 'LINK/USD', name: 'Chainlink', icon: '⬡' },
  { symbol: 'DOT/USD', name: 'Polkadot', icon: '●' },
  { symbol: 'MATIC/USD', name: 'Polygon', icon: '⬡' },
  { symbol: 'LTC/USD', name: 'Litecoin', icon: 'Ł' },
  { symbol: 'UNI/USD', name: 'Uniswap', icon: '🦄' },
  { symbol: 'SHIB/USD', name: 'Shiba Inu', icon: '🐕' },
  { symbol: 'ATOM/USD', name: 'Cosmos', icon: '⚛' },
  { symbol: 'BCH/USD', name: 'Bitcoin Cash', icon: '₿' },
  { symbol: 'AAVE/USD', name: 'Aave', icon: '👻' },
];

interface CryptoSelectorProps {
  selected: string[];
  onChange: (selected: string[]) => void;
  maxSelections?: number;
}

export default function CryptoSelector({ selected, onChange, maxSelections }: CryptoSelectorProps) {
  const toggleCrypto = (symbol: string) => {
    if (selected.includes(symbol)) {
      // Remove it
      onChange(selected.filter(s => s !== symbol));
    } else {
      // Add it (check max if specified)
      if (maxSelections && selected.length >= maxSelections) {
        return; // At max, don't add more
      }
      onChange([...selected, symbol]);
    }
  };

  const selectAll = () => {
    const allSymbols = AVAILABLE_CRYPTOS.map(c => c.symbol);
    if (maxSelections) {
      onChange(allSymbols.slice(0, maxSelections));
    } else {
      onChange(allSymbols);
    }
  };

  const clearAll = () => {
    onChange([]);
  };

  return (
    <div>
      {/* Header with count and actions */}
      <div className="flex items-center justify-between mb-3">
        <label className="block text-sm text-slate-400">
          Crypto Watchlist
          <span className="ml-2 text-xs text-slate-500">
            ({selected.length} of {AVAILABLE_CRYPTOS.length} selected)
          </span>
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={selectAll}
            className="text-xs px-2 py-1 text-orange-400 hover:text-orange-300 hover:bg-orange-500/10 rounded transition-colors"
          >
            Select All
          </button>
          <button
            type="button"
            onClick={clearAll}
            className="text-xs px-2 py-1 text-slate-400 hover:text-slate-300 hover:bg-slate-500/10 rounded transition-colors"
          >
            Clear All
          </button>
        </div>
      </div>

      {/* Crypto grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {AVAILABLE_CRYPTOS.map((crypto) => {
          const isSelected = selected.includes(crypto.symbol);
          const isDisabled = !isSelected && !!maxSelections && selected.length >= maxSelections;

          return (
            <button
              key={crypto.symbol}
              type="button"
              onClick={() => toggleCrypto(crypto.symbol)}
              disabled={isDisabled}
              className={`
                relative flex items-center gap-2 px-3 py-2 rounded-lg border transition-all
                ${isSelected
                  ? 'bg-orange-500/20 border-orange-500/50 text-white'
                  : 'bg-slate-700/50 border-slate-600/50 text-slate-300 hover:border-slate-500'
                }
                ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              {/* Checkmark indicator */}
              {isSelected && (
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-orange-500 rounded-full flex items-center justify-center">
                  <Check className="w-3 h-3 text-white" />
                </div>
              )}

              {/* Crypto icon/symbol */}
              <span className="text-lg w-6 text-center">{crypto.icon}</span>

              {/* Name and symbol */}
              <div className="text-left flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{crypto.symbol.replace('/USD', '')}</p>
                <p className="text-xs text-slate-400 truncate">{crypto.name}</p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Help text */}
      <p className="text-xs text-slate-500 mt-3">
        Select which cryptocurrencies the bot should scan for trading opportunities.
        The bot will analyze all selected cryptos each cycle.
      </p>
    </div>
  );
}
