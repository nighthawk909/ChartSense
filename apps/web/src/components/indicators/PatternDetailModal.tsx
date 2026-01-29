/**
 * PatternDetailModal - Shows detailed pattern visualization
 *
 * Displays pattern key points and draws a visual representation
 * of the detected pattern to help users understand what was found
 */
import { useEffect, useRef, useState } from 'react';
import { X, TrendingUp, TrendingDown, AlertCircle, Target, Info } from 'lucide-react';

interface PatternKeyPoint {
  index: number;
  price: number;
  label: string;
}

interface PatternLine {
  start_index: number;
  start_price: number;
  end_index: number;
  end_price: number;
  label: string;
  style: 'solid' | 'dashed';
}

interface Pattern {
  pattern: string;
  confidence: number;
  direction: string;
  description: string;
  price_target?: number;
  stop_loss?: number;
  start_index?: number;
  end_index?: number;
  key_points?: PatternKeyPoint[];
  pattern_lines?: PatternLine[];
}

interface PatternDetailModalProps {
  pattern: Pattern | null;
  symbol: string;
  onClose: () => void;
}

export default function PatternDetailModal({ pattern, symbol, onClose }: PatternDetailModalProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [canvasSize] = useState({ width: 600, height: 300 });

  useEffect(() => {
    if (!pattern || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Get key points data
    const keyPoints = pattern.key_points || [];
    const patternLines = pattern.pattern_lines || [];

    if (keyPoints.length === 0) {
      // No visualization data - show placeholder
      ctx.clearRect(0, 0, canvasSize.width, canvasSize.height);
      ctx.fillStyle = '#1e293b';
      ctx.fillRect(0, 0, canvasSize.width, canvasSize.height);
      ctx.fillStyle = '#64748b';
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Pattern visualization not available for this pattern type', canvasSize.width / 2, canvasSize.height / 2);
      return;
    }

    // Calculate price range from key points
    const prices = keyPoints.map(p => p.price);
    const minPrice = Math.min(...prices) * 0.995;
    const maxPrice = Math.max(...prices) * 1.005;
    const priceRange = maxPrice - minPrice;

    // Calculate index range
    const indices = keyPoints.map(p => p.index);
    const minIndex = Math.min(...indices) - 2;
    const maxIndex = Math.max(...indices) + 2;
    const indexRange = maxIndex - minIndex;

    // Padding
    const padding = { top: 50, right: 80, bottom: 40, left: 20 };
    const chartWidth = canvasSize.width - padding.left - padding.right;
    const chartHeight = canvasSize.height - padding.top - padding.bottom;

    // Convert functions
    const indexToX = (index: number): number => {
      return padding.left + ((index - minIndex) / indexRange) * chartWidth;
    };

    const priceToY = (price: number): number => {
      return padding.top + chartHeight - ((price - minPrice) / priceRange) * chartHeight;
    };

    // Clear and set background
    ctx.clearRect(0, 0, canvasSize.width, canvasSize.height);
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvasSize.width, canvasSize.height);

    // Draw grid
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;

    // Horizontal grid lines (prices)
    const priceStep = priceRange / 5;
    for (let i = 0; i <= 5; i++) {
      const price = minPrice + (priceStep * i);
      const y = priceToY(price);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(canvasSize.width - padding.right, y);
      ctx.stroke();

      // Price labels
      ctx.fillStyle = '#64748b';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(`$${price.toFixed(2)}`, canvasSize.width - 5, y + 3);
    }

    // Set up colors based on direction
    const primaryColor = pattern.direction === 'bullish' ? '#22c55e' : '#ef4444';
    const secondaryColor = pattern.direction === 'bullish' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)';
    const necklineColor = '#f59e0b';

    // Draw filled area if we have a polygon
    if (keyPoints.length >= 3) {
      ctx.beginPath();
      ctx.fillStyle = secondaryColor;
      keyPoints.forEach((point, i) => {
        const x = indexToX(point.index);
        const y = priceToY(point.price);
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.closePath();
      ctx.fill();
    }

    // Draw pattern lines
    patternLines.forEach((line) => {
      const x1 = indexToX(line.start_index);
      const y1 = priceToY(line.start_price);
      const x2 = indexToX(line.end_index);
      const y2 = priceToY(line.end_price);

      ctx.beginPath();
      ctx.strokeStyle = line.label.toLowerCase().includes('neckline') ? necklineColor : primaryColor;
      ctx.lineWidth = 2;

      if (line.style === 'dashed') {
        ctx.setLineDash([8, 4]);
      } else {
        ctx.setLineDash([]);
      }

      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();

      // Line label at midpoint
      if (line.label && !line.label.includes('-')) {
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
        ctx.font = 'bold 10px sans-serif';
        const labelWidth = ctx.measureText(line.label).width + 10;
        ctx.fillRect(midX - labelWidth / 2, midY - 9, labelWidth, 18);
        ctx.strokeStyle = line.label.toLowerCase().includes('neckline') ? necklineColor : primaryColor;
        ctx.lineWidth = 1;
        ctx.strokeRect(midX - labelWidth / 2, midY - 9, labelWidth, 18);
        ctx.fillStyle = '#e2e8f0';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(line.label, midX, midY);
      }
    });

    // Reset line dash
    ctx.setLineDash([]);

    // Draw key points
    keyPoints.forEach((point) => {
      const x = indexToX(point.index);
      const y = priceToY(point.price);

      // Outer glow
      ctx.beginPath();
      ctx.arc(x, y, 12, 0, Math.PI * 2);
      ctx.fillStyle = secondaryColor;
      ctx.fill();

      // Main circle
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fillStyle = '#0f172a';
      ctx.fill();
      ctx.strokeStyle = primaryColor;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Inner dot
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = primaryColor;
      ctx.fill();

      // Label background
      ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
      ctx.font = 'bold 11px sans-serif';
      const labelWidth = ctx.measureText(point.label).width + 14;
      const labelHeight = 24;
      const labelX = x - labelWidth / 2;
      const labelY = y - 35;

      // Rounded rectangle for label
      ctx.beginPath();
      ctx.roundRect(labelX, labelY, labelWidth, labelHeight, 4);
      ctx.fill();
      ctx.strokeStyle = primaryColor;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Label text
      ctx.fillStyle = '#f8fafc';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(point.label, x, labelY + labelHeight / 2);

      // Price below point
      ctx.font = '10px sans-serif';
      ctx.fillStyle = '#94a3b8';
      ctx.fillText(`$${point.price.toFixed(2)}`, x, y + 22);
    });

    // Draw title
    ctx.font = 'bold 14px sans-serif';
    ctx.fillStyle = '#f8fafc';
    ctx.textAlign = 'left';
    ctx.fillText(`${pattern.pattern} Pattern`, 10, 20);

    // Draw confidence badge
    ctx.font = 'bold 12px sans-serif';
    ctx.fillStyle = primaryColor;
    ctx.textAlign = 'right';
    ctx.fillText(`${pattern.confidence}% Confidence`, canvasSize.width - 10, 20);

  }, [pattern, canvasSize]);

  if (!pattern) return null;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-xl border border-slate-700 shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-auto">
        {/* Header */}
        <div className={`flex items-center justify-between p-4 border-b border-slate-700 ${
          pattern.direction === 'bullish' ? 'bg-green-900/20' : 'bg-red-900/20'
        }`}>
          <div className="flex items-center gap-3">
            {pattern.direction === 'bullish' ? (
              <TrendingUp className="w-6 h-6 text-green-400" />
            ) : pattern.direction === 'bearish' ? (
              <TrendingDown className="w-6 h-6 text-red-400" />
            ) : (
              <AlertCircle className="w-6 h-6 text-yellow-400" />
            )}
            <div>
              <h2 className="text-lg font-bold text-white">{pattern.pattern}</h2>
              <p className="text-sm text-slate-400">{symbol}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Canvas visualization */}
        <div className="p-4 bg-slate-900/50">
          <canvas
            ref={canvasRef}
            width={canvasSize.width}
            height={canvasSize.height}
            className="w-full rounded-lg border border-slate-700"
            style={{ maxWidth: '100%', height: 'auto' }}
          />
        </div>

        {/* Pattern details */}
        <div className="p-4 space-y-4">
          {/* Description */}
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
            <p className="text-sm text-slate-300">{pattern.description}</p>
          </div>

          {/* Targets and stops */}
          <div className="grid grid-cols-2 gap-4">
            {pattern.price_target && (
              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="flex items-center gap-2 text-green-400 mb-1">
                  <Target className="w-4 h-4" />
                  <span className="text-xs font-medium">Price Target</span>
                </div>
                <span className="text-lg font-bold text-white">${pattern.price_target.toFixed(2)}</span>
              </div>
            )}
            {pattern.stop_loss && (
              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="flex items-center gap-2 text-red-400 mb-1">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-xs font-medium">Stop Loss</span>
                </div>
                <span className="text-lg font-bold text-white">${pattern.stop_loss.toFixed(2)}</span>
              </div>
            )}
          </div>

          {/* Key points list */}
          {pattern.key_points && pattern.key_points.length > 0 && (
            <div className="bg-slate-700/30 rounded-lg p-3">
              <h3 className="text-sm font-medium text-slate-400 mb-2">Key Price Points</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {pattern.key_points.map((point, idx) => (
                  <div key={idx} className="flex justify-between text-sm">
                    <span className="text-slate-400">{point.label}:</span>
                    <span className="font-medium text-white">${point.price.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Confidence and direction indicators */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-700">
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                pattern.direction === 'bullish'
                  ? 'bg-green-500/20 text-green-400'
                  : pattern.direction === 'bearish'
                  ? 'bg-red-500/20 text-red-400'
                  : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {pattern.direction.charAt(0).toUpperCase() + pattern.direction.slice(1)}
              </span>
              <span className="text-sm text-slate-500">Signal</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    pattern.confidence >= 70 ? 'bg-green-500' :
                    pattern.confidence >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${pattern.confidence}%` }}
                />
              </div>
              <span className="text-sm font-medium text-white">{pattern.confidence}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
