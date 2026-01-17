import { useState, useEffect, useRef } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { TrendingUp, LayoutDashboard, Star, Settings, Bot, Search, X, Loader2, LineChart, History, Menu } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface SearchResult {
  symbol: string
  name: string
  type: string
  region: string
  matchScore?: string
}

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  const navItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/markets', icon: LineChart, label: 'Markets' },
    { path: '/watchlist', icon: Star, label: 'Watchlist' },
    { path: '/analysis-history', icon: History, label: 'Analysis History' },
    { path: '/bot', icon: Bot, label: 'Trading Bot' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ]

  // Close sidebar when route changes (mobile)
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  // Handle click outside to close search results
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Debounced search
  useEffect(() => {
    if (searchTimeout.current) {
      clearTimeout(searchTimeout.current)
    }

    if (searchQuery.length < 1) {
      setSearchResults([])
      setShowResults(false)
      return
    }

    searchTimeout.current = setTimeout(async () => {
      setIsSearching(true)
      try {
        const response = await fetch(`${API_URL}/api/stocks/search?query=${encodeURIComponent(searchQuery)}`)
        if (response.ok) {
          const data = await response.json()
          setSearchResults(data.results || [])
          setShowResults(true)
        }
      } catch (error) {
        console.error('Search failed:', error)
        setSearchResults([])
      } finally {
        setIsSearching(false)
      }
    }, 300) // 300ms debounce

    return () => {
      if (searchTimeout.current) {
        clearTimeout(searchTimeout.current)
      }
    }
  }, [searchQuery])

  const handleSelectStock = (symbol: string) => {
    setSearchQuery('')
    setShowResults(false)
    setSidebarOpen(false)
    navigate(`/stock/${symbol}`)
  }

  const clearSearch = () => {
    setSearchQuery('')
    setSearchResults([])
    setShowResults(false)
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 py-3 flex items-center justify-between gap-2 sm:gap-4">
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <Menu className="h-5 w-5" />
          </button>

          <Link to="/dashboard" className="flex items-center gap-2 shrink-0">
            <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-blue-500" />
            <span className="text-lg sm:text-xl font-bold hidden sm:inline">ChartSense</span>
          </Link>

          {/* Search */}
          <div className="flex-1 max-w-md mx-2 sm:mx-8 relative" ref={searchRef}>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => searchResults.length > 0 && setShowResults(true)}
                placeholder="Search stocks (e.g., AAPL, MSFT)"
                className="w-full pl-10 pr-10 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm sm:text-base"
              />
              {isSearching && (
                <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400 animate-spin" />
              )}
              {!isSearching && searchQuery && (
                <button
                  onClick={clearSearch}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Search Results Dropdown */}
            {showResults && searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-600 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto">
                {searchResults.map((result) => (
                  <button
                    key={result.symbol}
                    onClick={() => handleSelectStock(result.symbol)}
                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700 transition-colors border-b border-slate-700 last:border-b-0"
                  >
                    <div className="flex flex-col items-start">
                      <span className="font-semibold text-white">{result.symbol}</span>
                      <span className="text-sm text-slate-400 truncate max-w-[200px] sm:max-w-[250px]">{result.name}</span>
                    </div>
                    <span className="text-xs text-slate-500 bg-slate-700 px-2 py-1 rounded">{result.type}</span>
                  </button>
                ))}
              </div>
            )}

            {/* No Results */}
            {showResults && searchQuery && searchResults.length === 0 && !isSearching && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-600 rounded-lg shadow-lg z-50 p-4 text-center text-slate-400">
                No stocks found for "{searchQuery}"
              </div>
            )}
          </div>

          {/* Settings */}
          <Link to="/settings" className="p-2 hover:bg-slate-700 rounded-lg transition-colors shrink-0">
            <Settings className="h-5 w-5" />
          </Link>
        </div>
      </header>

      <div className="flex relative">
        {/* Mobile sidebar overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <nav className={`
          fixed lg:static inset-y-0 left-0 z-40
          w-64 bg-slate-800 min-h-[calc(100vh-60px)] p-4 border-r border-slate-700
          transform transition-transform duration-200 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          top-[60px] lg:top-0
        `}>
          <ul className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon
              // Handle active state - dashboard is special case
              const isActive = location.pathname === item.path ||
                (item.path === '/dashboard' && location.pathname === '/')
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Main Content */}
        <main className="flex-1 p-3 sm:p-6 w-full lg:w-auto min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
