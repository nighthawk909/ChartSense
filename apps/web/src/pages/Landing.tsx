/**
 * Landing Page
 * Marketing/welcome page with "Launch App" button that routes to dashboard
 */
import { Link } from 'react-router-dom';
import { TrendingUp, Bot, LineChart, Shield, Zap, ArrowRight, Github } from 'lucide-react';

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      {/* Header */}
      <header className="container mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-8 w-8 text-blue-500" />
          <span className="text-2xl font-bold">ChartSense</span>
        </div>
        <nav className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-slate-300 hover:text-white transition-colors">Features</a>
          <a href="#about" className="text-slate-300 hover:text-white transition-colors">About</a>
          <Link
            to="/dashboard"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors"
          >
            Launch App
          </Link>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-6 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-400 via-purple-400 to-blue-400 bg-clip-text text-transparent">
            AI-Powered Trading Intelligence
          </h1>
          <p className="text-xl text-slate-300 mb-10 max-w-2xl mx-auto">
            ChartSense combines real-time market analysis with AI-driven insights to help you make smarter trading decisions across stocks and crypto markets.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/dashboard"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-xl text-lg font-semibold transition-all hover:scale-105 shadow-lg shadow-blue-500/25"
            >
              Launch App
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              to="/bot"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-slate-700 hover:bg-slate-600 rounded-xl text-lg font-semibold transition-all hover:scale-105"
            >
              <Bot className="w-5 h-5" />
              Trading Bot
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="container mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">Powerful Features</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="p-6 bg-slate-800/50 rounded-2xl border border-slate-700 hover:border-blue-500/50 transition-colors">
            <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center mb-4">
              <LineChart className="w-6 h-6 text-blue-400" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Technical Analysis</h3>
            <p className="text-slate-400">
              Real-time RSI, MACD, Bollinger Bands, and moving averages with interactive charts powered by TradingView.
            </p>
          </div>

          <div className="p-6 bg-slate-800/50 rounded-2xl border border-slate-700 hover:border-purple-500/50 transition-colors">
            <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mb-4">
              <Bot className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="text-xl font-semibold mb-2">AI Trading Bot</h3>
            <p className="text-slate-400">
              Automated trading with AI-powered decision making. 24/7 crypto monitoring and smart stock scanning during market hours.
            </p>
          </div>

          <div className="p-6 bg-slate-800/50 rounded-2xl border border-slate-700 hover:border-green-500/50 transition-colors">
            <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-green-400" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Real-Time Data</h3>
            <p className="text-slate-400">
              Live market data for stocks and cryptocurrencies with instant updates and force-refresh capabilities.
            </p>
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section className="container mx-auto px-6 py-16">
        <div className="bg-slate-800/30 rounded-3xl p-8 md:p-12 border border-slate-700">
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div className="flex-shrink-0">
              <div className="w-20 h-20 bg-green-500/20 rounded-2xl flex items-center justify-center">
                <Shield className="w-10 h-10 text-green-400" />
              </div>
            </div>
            <div>
              <h3 className="text-2xl font-bold mb-2">Paper Trading First</h3>
              <p className="text-slate-400 text-lg">
                Start with paper trading to test strategies risk-free. ChartSense integrates with Alpaca's paper trading API,
                so you can practice without risking real money until you're confident.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-6 py-20 text-center">
        <h2 className="text-3xl font-bold mb-4">Ready to Trade Smarter?</h2>
        <p className="text-slate-400 mb-8 text-lg">
          Join ChartSense and start making data-driven trading decisions today.
        </p>
        <Link
          to="/dashboard"
          className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-xl text-lg font-semibold transition-all hover:scale-105 shadow-lg shadow-blue-500/25"
        >
          Launch App Now
          <ArrowRight className="w-5 h-5" />
        </Link>
      </section>

      {/* Footer */}
      <footer id="about" className="border-t border-slate-800 py-12">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-6 w-6 text-blue-500" />
              <span className="text-lg font-semibold">ChartSense</span>
            </div>
            <p className="text-slate-500 text-sm">
              Technical analysis trading platform with AI-powered insights.
            </p>
            <div className="flex items-center gap-4">
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-400 hover:text-white transition-colors"
              >
                <Github className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
