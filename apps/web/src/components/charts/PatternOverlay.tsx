/**
 * PatternOverlay - Displays pattern visualization on TradingView chart
 *
 * Shows pattern key points (e.g., Head, Shoulders, Neckline) as markers
 * and draws pattern lines connecting them
 */
import { useEffect, useRef, useState } from 'react';
import { X, ZoomIn, Info } from 'lucide-react';

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
  key_points?: PatternKeyPoint[];
  pattern_lines?: PatternLine[];
}

interface ChartBar {
  time: number | string;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface PatternOverlayProps {
  pattern: Pattern | null;
  chartBars: ChartBar[];
  chartWidth: number;
  chartHeight: number;
  priceRange: { min: number; max: number };
  visibleRange: { startIndex: number; endIndex: number };
  onClose: () => void;
}

export default function PatternOverlay({
  pattern,
  chartBars,
  chartWidth,
  chartHeight,
  priceRange,
  visibleRange,
  onClose,
}: PatternOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [showInfo, setShowInfo] = useState(false);

  // Convert bar index to X coordinate
  const indexToX = (index: number): number => {
    const barsInView = visibleRange.endIndex - visibleRange.startIndex;
    const adjustedIndex = index - visibleRange.startIndex;
    return (adjustedIndex / barsInView) * chartWidth;
  };

  // Convert price to Y coordinate
  const priceToY = (price: number): number => {
    const range = priceRange.max - priceRange.min;
    return chartHeight - ((price - priceRange.min) / range) * chartHeight;
  };

  useEffect(() => {
    if (!pattern || !canvasRef.current || !pattern.key_points) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, chartWidth, chartHeight);

    // Set up colors based on pattern direction
    const primaryColor = pattern.direction === 'bullish' ? '#22c55e' : '#ef4444';
    const secondaryColor = pattern.direction === 'bullish' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)';
    const necklineColor = '#f59e0b';

    // Draw pattern lines first (behind points)
    if (pattern.pattern_lines) {
      pattern.pattern_lines.forEach((line) => {
        const x1 = indexToX(line.start_index);
        const y1 = priceToY(line.start_price);
        const x2 = indexToX(line.end_index);
        const y2 = priceToY(line.end_price);

        ctx.beginPath();
        ctx.strokeStyle = line.label.toLowerCase().includes('neckline') ? necklineColor : primaryColor;
        ctx.lineWidth = 2;

        if (line.style === 'dashed') {
          ctx.setLineDash([5, 5]);
        } else {
          ctx.setLineDash([]);
        }

        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();

        // Draw line label at midpoint
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
        ctx.font = '10px sans-serif';
        const labelWidth = ctx.measureText(line.label).width + 8;
        ctx.fillRect(midX - labelWidth / 2, midY - 8, labelWidth, 16);
        ctx.fillStyle = line.label.toLowerCase().includes('neckline') ? necklineColor : primaryColor;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(line.label, midX, midY);
      });
    }

    // Draw key points
    ctx.setLineDash([]);
    pattern.key_points.forEach((point) => {
      const x = indexToX(point.index);
      const y = priceToY(point.price);

      // Draw circle marker
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fillStyle = secondaryColor;
      ctx.fill();
      ctx.strokeStyle = primaryColor;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw inner dot
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = primaryColor;
      ctx.fill();

      // Draw label
      ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
      ctx.font = 'bold 11px sans-serif';
      const labelWidth = ctx.measureText(point.label).width + 12;
      const labelHeight = 20;
      const labelX = x - labelWidth / 2;
      const labelY = y - 25;

      // Label background with rounded corners
      ctx.beginPath();
      ctx.roundRect(labelX, labelY, labelWidth, labelHeight, 4);
      ctx.fill();

      // Label border
      ctx.strokeStyle = primaryColor;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Label text
      ctx.fillStyle = '#e2e8f0';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(point.label, x, labelY + labelHeight / 2);

      // Price label
      ctx.font = '10px sans-serif';
      ctx.fillStyle = '#94a3b8';
      ctx.fillText(`$${point.price.toFixed(2)}`, x, labelY + labelHeight + 12);
    });

  }, [pattern, chartBars, chartWidth, chartHeight, priceRange, visibleRange]);

  if (!pattern) return null;

  return (
    <div className="absolute inset-0 pointer-events-none">
      {/* Pattern info header */}
      <div className="absolute top-2 left-2 right-2 pointer-events-auto">
        <div className={`flex items-center justify-between p-2 rounded-lg ${
          pattern.direction === 'bullish' ? 'bg-green-900/80' : 'bg-red-900/80'
        } backdrop-blur-sm border ${
          pattern.direction === 'bullish' ? 'border-green-500/50' : 'border-red-500/50'
        }`}>
          <div className="flex items-center gap-2">
            <ZoomIn className="w-4 h-4 text-slate-300" />
            <span className="font-semibold text-white text-sm">{pattern.pattern}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              pattern.direction === 'bullish' ? 'bg-green-600' : 'bg-red-600'
            } text-white`}>
              {pattern.confidence}% conf
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowInfo(!showInfo)}
              className="p-1 hover:bg-slate-700/50 rounded"
              title="Pattern details"
            >
              <Info className="w-4 h-4 text-slate-300" />
            </button>
            <button
              onClick={onClose}
              className="p-1 hover:bg-slate-700/50 rounded"
              title="Close overlay"
            >
              <X className="w-4 h-4 text-slate-300" />
            </button>
          </div>
        </div>

        {/* Pattern description popup */}
        {showInfo && (
          <div className="mt-2 p-3 bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-lg text-sm">
            <p className="text-slate-300 mb-2">{pattern.description}</p>
            {pattern.key_points && (
              <div className="text-xs text-slate-400">
                <p className="font-medium mb-1">Key Points:</p>
                <ul className="space-y-1">
                  {pattern.key_points.map((point, idx) => (
                    <li key={idx} className="flex justify-between">
                      <span>{point.label}:</span>
                      <span className="text-slate-300">${point.price.toFixed(2)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Canvas overlay for drawing */}
      <canvas
        ref={canvasRef}
        width={chartWidth}
        height={chartHeight}
        className="absolute inset-0"
      />
    </div>
  );
}
