import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'
import Watchlist from './pages/Watchlist'
import TradingBot from './pages/TradingBot'
import Settings from './pages/Settings'
import Crypto from './pages/Crypto'
import Markets from './pages/Markets'
import AnalysisHistory from './pages/AnalysisHistory'

function App() {
  return (
    <Routes>
      {/* Landing page (marketing/welcome) */}
      <Route path="/" element={<Landing />} />

      {/* App routes with Layout */}
      <Route path="/dashboard" element={<Layout />}>
        <Route index element={<Dashboard />} />
      </Route>
      <Route element={<Layout />}>
        <Route path="stock/:symbol" element={<StockDetail />} />
        <Route path="watchlist" element={<Watchlist />} />
        <Route path="bot" element={<TradingBot />} />
        <Route path="settings" element={<Settings />} />
        <Route path="crypto" element={<Crypto />} />
        <Route path="markets" element={<Markets />} />
        <Route path="analysis-history" element={<AnalysisHistory />} />
      </Route>
    </Routes>
  )
}

export default App
