/**
 * Activity Log Component
 * Shows recent bot activity, decisions, and events
 * Now includes crypto scanning activity
 */
import { Activity, Info, AlertTriangle, AlertCircle, Clock, TrendingUp, Eye, Search, CheckCircle, Bitcoin, BarChart3, Zap, Settings } from 'lucide-react';

interface ActivityItem {
  timestamp: string | null;
  type: string;
  message: string;
  level: 'info' | 'warning' | 'error' | 'success';
}

interface ActivityLogProps {
  activities: ActivityItem[];
  loading?: boolean;
}

export default function ActivityLog({ activities, loading }: ActivityLogProps) {
  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 animate-pulse">
        <div className="h-6 bg-slate-700 rounded w-32 mb-4"></div>
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-8 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  const getIcon = (type: string, level: string) => {
    if (level === 'error') return <AlertCircle className="w-4 h-4 text-red-400" />;
    if (level === 'warning') return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
    if (level === 'success') return <CheckCircle className="w-4 h-4 text-green-400" />;

    switch (type) {
      case 'cycle':
        return <Activity className="w-4 h-4 text-blue-400" />;
      case 'market':
        return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'symbols':
        return <Eye className="w-4 h-4 text-purple-400" />;
      case 'uptime':
        return <Clock className="w-4 h-4 text-cyan-400" />;
      case 'crypto_scan':
        return <Bitcoin className="w-4 h-4 text-orange-400" />;
      case 'crypto_signal':
        return <Bitcoin className="w-4 h-4 text-green-400" />;
      case 'stock_scan':
        return <BarChart3 className="w-4 h-4 text-blue-400" />;
      case 'stock_signal':
        return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'mode':
        return <Settings className="w-4 h-4 text-slate-400" />;
      case 'positions':
        return <Eye className="w-4 h-4 text-purple-400" />;
      case 'scans':
        return <Search className="w-4 h-4 text-cyan-400" />;
      case 'state':
        return <Zap className="w-4 h-4 text-yellow-400" />;
      default:
        return <Info className="w-4 h-4 text-slate-400" />;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'border-l-red-500 bg-red-500/5';
      case 'warning':
        return 'border-l-yellow-500 bg-yellow-500/5';
      case 'success':
        return 'border-l-green-500 bg-green-500/5';
      default:
        return 'border-l-slate-600 bg-slate-700/30';
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-500" />
          Bot Activity
        </h3>
        <span className="text-xs text-slate-500">Live</span>
      </div>

      {activities.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No recent activity</p>
          <p className="text-xs">Start the bot to see activity here</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {activities.map((activity, index) => (
            <div
              key={index}
              className={`flex items-start gap-3 p-3 rounded-lg border-l-2 ${getLevelColor(activity.level)}`}
            >
              <div className="flex-shrink-0 mt-0.5">
                {getIcon(activity.type, activity.level)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white">{activity.message}</p>
                {activity.timestamp && (
                  <p className="text-xs text-slate-500 mt-1">
                    {new Date(activity.timestamp).toLocaleTimeString()}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-slate-700">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Auto-refreshes every 5s</span>
          <span>{activities.length} events</span>
        </div>
      </div>
    </div>
  );
}
