import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'
import Watchlist from './pages/Watchlist'
import TradingBot from './pages/TradingBot'
import Settings from './pages/Settings'
import Crypto from './pages/Crypto'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="stock/:symbol" element={<StockDetail />} />
        <Route path="watchlist" element={<Watchlist />} />
        <Route path="bot" element={<TradingBot />} />
        <Route path="settings" element={<Settings />} />
        <Route path="crypto" element={<Crypto />} />
      </Route>
    </Routes>
  )
}

export default App
