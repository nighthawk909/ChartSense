import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'
import Watchlist from './pages/Watchlist'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="stock/:symbol" element={<StockDetail />} />
        <Route path="watchlist" element={<Watchlist />} />
      </Route>
    </Routes>
  )
}

export default App
