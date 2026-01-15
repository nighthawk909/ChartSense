# ChartSense

> AI-powered stock trading app focused on technical analysis with fundamental insights.

## Overview

ChartSense helps traders make informed decisions by combining:
- **Technical Analysis**: Chart patterns, indicators (RSI, MACD, Bollinger Bands, etc.)
- **Fundamental Analysis**: Key metrics, earnings, financial ratios
- **AI Insights**: Pattern recognition and trade suggestions

## Tech Stack

| Component | Technology |
|-----------|------------|
| Web App | React + TypeScript + Vite + Tailwind CSS |
| API Backend | FastAPI (Python) |
| Stock Data | Alpha Vantage API |
| Charts | TradingView Lightweight Charts / Recharts |
| Database | SQLite (dev) / PostgreSQL (prod) |
| AI/LLM | OpenAI GPT-4 (optional) |

## Project Structure

```
ChartSense/
├── apps/
│   └── web/                 # React web application
│       ├── src/
│       │   ├── components/  # Reusable UI components
│       │   ├── pages/       # Route pages
│       │   ├── hooks/       # Custom React hooks
│       │   ├── services/    # API calls, data fetching
│       │   ├── types/       # TypeScript types
│       │   └── utils/       # Helper functions
│       └── public/
├── api/                     # FastAPI backend
│   ├── routes/              # API endpoints
│   ├── services/            # Business logic
│   ├── models/              # Pydantic models
│   └── database/            # SQLAlchemy models
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
└── tests/                   # Test suites
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- Alpha Vantage API key (free at https://www.alphavantage.co/support/#api-key)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/ChartSense.git
cd ChartSense

# Install web app dependencies
cd apps/web
npm install

# Install API dependencies
cd ../../api
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add your Alpha Vantage API key to .env
```

### Running the App

```bash
# Start the web app (from apps/web/)
npm run dev

# Start the API server (from api/)
uvicorn main:app --reload
```

## Features (Planned)

- [ ] Real-time stock quotes and charts
- [ ] Technical indicators (RSI, MACD, SMA, EMA, Bollinger Bands)
- [ ] Watchlist management
- [ ] Price alerts
- [ ] Trade journal
- [ ] AI-powered pattern recognition
- [ ] Fundamental data display (P/E, EPS, etc.)
- [ ] Portfolio tracking

## License

MIT License
