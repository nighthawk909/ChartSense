/**
 * Asset Class Toggle Component
 * Switch between Crypto Only, Stocks Only, or Hybrid/Both trading modes
 */
import { Bitcoin, TrendingUp, Layers } from 'lucide-react';

export type AssetClassMode = 'crypto' | 'stocks' | 'both';

interface AssetClassToggleProps {
  mode: AssetClassMode;
  onChange: (mode: AssetClassMode) => void;
  disabled?: boolean;
  scanCount?: number;
  isActive?: boolean;
}

export default function AssetClassToggle({
  mode,
  onChange,
  disabled = false,
  scanCount = 0,
  isActive = false,
}: AssetClassToggleProps) {
  const options: { value: AssetClassMode; label: string; icon: typeof Bitcoin; description: string }[] = [
    {
      value: 'crypto',
      label: 'Crypto',
      icon: Bitcoin,
      description: '24/7 crypto trading',
    },
    {
      value: 'stocks',
      label: 'Stocks',
      icon: TrendingUp,
      description: 'Market hours only',
    },
    {
      value: 'both',
      label: 'Both',
      icon: Layers,
      description: 'Hybrid trading',
    },
  ];

  return (
    <div className="flex items-center gap-4">
      {/* Asset Class Buttons */}
      <div className="flex bg-slate-700/50 rounded-lg p-1">
        {options.map((option) => (
          <button
            key={option.value}
            onClick={() => onChange(option.value)}
            disabled={disabled}
            className={`flex items-center gap-2 px-3 py-2 rounded-md transition-all text-sm font-medium
                     disabled:opacity-50 disabled:cursor-not-allowed
                     ${mode === option.value
                       ? 'bg-slate-600 text-white shadow-md'
                       : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                     }`}
            title={option.description}
          >
            <option.icon className={`w-4 h-4 ${
              mode === option.value
                ? option.value === 'crypto' ? 'text-orange-400'
                : option.value === 'stocks' ? 'text-green-400'
                : 'text-purple-400'
                : ''
            }`} />
            <span className="hidden sm:inline">{option.label}</span>
          </button>
        ))}
      </div>

      {/* Status Indicators */}
      <div className="flex items-center gap-3 text-xs">
        {/* Bot Active Indicator */}
        {isActive && (
          <div className="flex items-center gap-1.5 px-2 py-1 bg-green-500/20 text-green-400 rounded">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span>Bot Active</span>
          </div>
        )}

        {/* Scan Count */}
        {scanCount > 0 && (
          <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-500/20 text-blue-400 rounded">
            <span>Scans: {scanCount.toLocaleString()}</span>
          </div>
        )}
      </div>
    </div>
  );
}
