# AosiConn Trading Platform

A modern, production-ready cryptocurrency trading backend with multi-exchange support, comprehensive analytics, and real-time WebSocket updates.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [API Documentation](#api-documentation)
- [Strategy Development](#strategy-development)
- [Database Schema](#database-schema)
- [Troubleshooting](#troubleshooting)

## Overview

AosiConn is a sophisticated trading platform designed for automated cryptocurrency trading. It provides a robust backend API, a modern web dashboard, and a flexible strategy execution engine that supports multiple exchanges.

### Key Capabilities

- **Multi-Exchange Trading**: Currently supports Hyperliquid, dYdX, and BitMEX
- **Strategy Engine**: Upload and execute custom trading strategies
- **Real-time Analytics**: Live P&L tracking, performance metrics, and visualizations
- **WebSocket API**: Real-time data streaming for dashboard updates
- **Secure Authentication**: JWT-based authentication with encrypted API keys
- **Comprehensive Logging**: Trade history, metrics, and position tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AosiConn Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   Dashboard  │     │   REST API   │     │  WebSocket   │                │
│  │   (Vue.js)   │◄────┤   (FastAPI)  │◄────┤   Manager    │                │
│  └──────────────┘     └──────┬───────┘     └──────────────┘                │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Core Services                               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐        │   │
│  │  │  Auth    │  │  Thread  │  │ Exchange │  │   Metrics    │        │   │
│  │  │ Handler  │  │ Manager  │  │ Adapters │  │  Calculator  │        │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘        │   │
│  └───────┼─────────────┼─────────────┼───────────────┼────────────────┘   │
│          │             │             │               │                     │
│          ▼             ▼             ▼               ▼                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Data Layer                                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐        │   │
│  │  │  Users   │  │  Trades  │  │ Balance  │  │    Keys      │        │   │
│  │  ├──────────┤  ├──────────┤  ├──────────┤  ├──────────────┤        │   │
│  │  │ Threads  │  │  Daily   │  │ Position │  │   Strategy   │        │   │
│  │  │          │  │ Metrics  │  │ Snapshots│  │ Performance  │        │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘        │   │
│  │                                                                    │   │
│  │                    SQLite / PostgreSQL (SQLAlchemy)                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. FastAPI Application (`core/app/main.py`)
- Main entry point for the application
- Configures CORS, middleware, and routers
- Manages application lifespan (startup/shutdown)
- Registers event loop for cross-thread WebSocket broadcasts

#### 2. Authentication System (`core/app/auth/`)
- **JWT Handler**: Token generation and validation
- **Bearer Auth**: FastAPI dependency for protected routes
- **Crypt Utils**: API key encryption/decryption
- Password hashing with bcrypt

#### 3. Exchange Adapters (`core/app/exchange/`)
Each exchange implements a common interface:
- **Hyperliquid**: Main exchange integration
- **dYdX**: dYdX v4 protocol support
- **BitMEX**: BitMEX API integration

All adapters provide:
- Market data retrieval
- Order placement/management
- Position tracking
- Balance queries

#### 4. Strategy Execution Engine (`core/app/utils/thread_utils.py`)
- **ThreadTemplate**: Base class for all strategies
- Automatic trade recording and P&L calculation
- Position snapshot management
- WebSocket event broadcasting
- Database session management per thread

#### 5. Database Layer (`core/app/db/`)
SQLAlchemy ORM with models for:
- User management
- Trade records with full P&L tracking
- Balance snapshots
- Thread/strategy state
- Performance metrics
- Position snapshots

#### 6. WebSocket Manager (`core/app/utils/websocket_manager.py`)
- Connection management for live dashboard updates
- Room-based subscriptions (per-user channels)
- Event broadcasting from background threads
- Automatic reconnection support

#### 7. Metrics Service (`core/app/utils/metrics_service.py`)
- Real-time performance calculations
- Drawdown tracking
- Win rate and profit factor computation
- Daily aggregation
- Strategy performance comparison

## Features

### Trading Features

| Feature | Description |
|---------|-------------|
| Multi-Exchange | Trade across multiple exchanges from one platform |
| Strategy Upload | Upload strategies as ZIP files with config |
| Position Tracking | Real-time position monitoring with P&L |
| Risk Management | Stop-loss, take-profit, and leverage controls |
| Order Types | Market, limit, and stop orders |

### Analytics Features

| Metric | Description |
|--------|-------------|
| Total P&L | Cumulative profit/loss across all trades |
| Win Rate | Percentage of winning trades |
| Profit Factor | Gross profit / Gross loss ratio |
| Expectancy | Average expected return per trade |
| Max Drawdown | Largest peak-to-trough decline |
| Sharpe Ratio | Risk-adjusted return measure |
| Consecutive Streaks | Max consecutive wins/losses |

### Dashboard Features

- **Real-time Updates**: WebSocket-powered live data
- **Equity Curve**: Interactive balance history chart
- **Drawdown Analysis**: Visualize drawdown periods
- **Daily P&L**: Bar chart of daily performance
- **Position Heatmap**: Trading activity visualization
- **Strategy Comparison**: Performance per strategy
- **Export**: CSV export for all data

## Quick Start

### Prerequisites

- Python 3.13+
- uv (Python package manager)
- Git

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd AosiConn
```

2. **Install uv (if not already installed)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. **Install dependencies**
```bash
uv sync
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
nano .env
```

5. **Run the application**
```bash
cd core/app
uv run python main.py
```

6. **Access the application**
- API: http://localhost:8000
- Dashboard: http://localhost:8000/dashboard
- API Docs: http://localhost:8000/docs

## Development Setup

### Project Structure

```
AosiConn/
├── core/
│   ├── app/                     # Main application
│   │   ├── auth/               # Authentication modules
│   │   ├── db/                 # Database models and CRUD
│   │   ├── exchange/           # Exchange adapters
│   │   ├── logger/             # Logging utilities
│   │   ├── routes/             # API route handlers
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── static/             # Static files (dashboard)
│   │   ├── threads/            # Strategy storage
│   │   ├── utils/              # Utility modules
│   │   └── main.py             # Application entry point
│   ├── train/                  # ML training data and notebooks
│   └── Dockerfile              # Legacy Dockerfile
├── deploy/                     # Deployment configurations
│   └── systemd/               # Systemd service files
├── data/                       # Data directory (created at runtime)
├── pyproject.toml             # Project dependencies
├── uv.lock                    # Locked dependency versions
├── docker-compose.yml         # Docker Compose configuration
├── Dockerfile                 # Main Dockerfile (uv-based)
└── README.md                  # This file
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection URL | `sqlite:///db/aosiconn.db` |
| `JWT_SECRET_KEY` | Secret for JWT signing | Required |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html
```

## Production Deployment

### Option 1: Docker Deployment (Recommended)

1. **Build and run**
```bash
docker-compose up -d
```

2. **With Nginx reverse proxy**
```bash
docker-compose --profile production up -d
```

3. **View logs**
```bash
docker-compose logs -f aosiconn
```

### Option 2: Systemd Service

1. **Run the install script**
```bash
sudo ./deploy/systemd/install.sh
```

2. **Or install manually**
```bash
# Copy service file
sudo cp deploy/systemd/aosiconn.service /etc/systemd/system/

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable aosiconn
sudo systemctl start aosiconn
```

3. **Check status**
```bash
sudo systemctl status aosiconn
sudo journalctl -u aosiconn -f
```

See [deploy/systemd/README.md](deploy/systemd/README.md) for detailed instructions.

### Option 3: Manual Deployment

1. **Create user**
```bash
sudo useradd -r -s /bin/false aosiconn
```

2. **Install application**
```bash
sudo mkdir -p /opt/aosiconn
sudo cp -r core pyproject.toml uv.lock /opt/aosiconn/
sudo chown -R aosiconn:aosiconn /opt/aosiconn
```

3. **Install dependencies**
```bash
cd /opt/aosiconn
sudo uv sync
```

4. **Create data directories**
```bash
sudo mkdir -p /opt/aosiconn/data/{db,logs,threads}
sudo chown -R aosiconn:aosiconn /opt/aosiconn/data
```

5. **Configure environment**
```bash
sudo nano /opt/aosiconn/.env
```

6. **Create startup script**
```bash
sudo tee /opt/aosiconn/start.sh << 'EOF'
#!/bin/bash
cd /opt/aosiconn/core/app
exec uv run python main.py
EOF
sudo chmod +x /opt/aosiconn/start.sh
```

7. **Run with process manager**
Use PM2, Supervisor, or screen/tmux for process management.

### Security Checklist

- [ ] Change default `JWT_SECRET_KEY`
- [ ] Use strong database credentials (if using PostgreSQL)
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure proper CORS origins
- [ ] Set up firewall rules (allow only necessary ports)
- [ ] Enable fail2ban for SSH protection
- [ ] Regular security updates
- [ ] Encrypt sensitive environment variables
- [ ] Use secrets management for API keys

## API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create new user account |
| POST | `/auth/login` | Login and get JWT token |

### Trading Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/exchange/balance/{exchange}` | Get account balance |
| GET | `/exchange/position/{exchange}/{pair}` | Get position info |
| POST | `/exchange/open/{exchange}` | Open position |
| POST | `/exchange/close/{exchange}` | Close position |

### Thread/Strategy Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/thread/all` | List all threads |
| POST | `/thread/start` | Start new strategy thread |
| POST | `/thread/stop/{id}` | Stop thread |
| POST | `/thread/upload` | Upload strategy |

### Statistics Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats/performance` | Performance summary |
| GET | `/stats/equity-curve` | Balance history |
| GET | `/stats/daily-metrics` | Daily aggregated data |
| GET | `/stats/strategy-performance` | Per-strategy metrics |
| GET | `/stats/position-heatmap` | Position activity heatmap |
| GET | `/stats/returns` | Period returns |
| GET | `/stats/drawdowns` | Drawdown history |

### WebSocket Events

**Client → Server:**
- `get_performance` - Request performance summary
- `get_positions` - Request position snapshots
- `get_balance` - Request balance update
- `get_equity_curve` - Request equity curve data
- `subscribe` - Subscribe to channels

**Server → Client:**
- `trade_update` - New or closed trade
- `position_update` - Position snapshot update
- `balance_update` - Balance change
- `metrics_update` - Daily metrics update

## Strategy Development

### Strategy Structure

Strategies are uploaded as ZIP files containing:

```
strategy.zip
├── main.py          # Strategy implementation
└── config.json      # Strategy configuration
```

### config.json

```json
{
  "name": "MyStrategy",
  "description": "Moving average crossover strategy",
  "author": "Your Name",
  "version": "1.0.0",
  "interval": 60
}
```

### main.py Template

```python
from utils.thread_utils import ThreadTemplate

class Strategy(ThreadTemplate):
    def __init__(self, thread_id, user_id, pair, exchange, qty, leverage, message):
        super().__init__(thread_id, user_id, pair, exchange, qty, leverage, message)
        self.strategy_name = 'MyStrategy'
    
    def execute(self):
        super().execute()
        
        # Your strategy logic here
        # Example: Get market data
        ticker = self.client.get_ticker()
        current_price = float(ticker['last'])
        
        # Example: Create a trade
        if self.should_enter_long(current_price):
            trade = self.create_trade(
                action=1,  # Buy
                entry_price=current_price,
                stop_loss=current_price * 0.95,
                take_profit=current_price * 1.10
            )
        
        # Record position snapshot
        self.record_position_snapshot(
            position_size=1.5,
            entry_price=current_price,
            mark_price=current_price,
            unrealized_pnl=0.0,
            margin_used=150.0,
            leverage=10,
            position_value=1500.0
        )
    
    def should_enter_long(self, price):
        # Your entry logic
        return False
```

### ThreadTemplate API

| Method | Description |
|--------|-------------|
| `create_trade(...)` | Create and record a new trade |
| `close_trade(trade_id, exit_price)` | Close an existing trade |
| `record_position_snapshot(...)` | Record position state |
| `send_ws_message(event, data)` | Send WebSocket update |
| `update_heartbeat()` | Update thread heartbeat |

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    users    │       │    trades   │       │  threads    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────┤ user_id     │       │ id (PK)     │
│ name        │       │ exchange    │       │ user_id     │◄─┐
│ username    │       │ pair        │       │ pair        │  │
│ password    │       │ qty         │       │ exchange    │  │
│ created_at  │       │ leverage    │       │ leverage    │  │
└─────────────┘       │ action      │       │ strategy    │  │
                      │ result      │       │ status      │  │
┌─────────────┐       │ entry_price │       │ created_at  │  │
│    keys     │       │ exit_price  │       └─────────────┘  │
├─────────────┤       │ pnl_abs     │              │          │
│ id (PK)     │       │ pnl_pct     │              │          │
│ user_id     │◄──────┤ status      │              │          │
│ exchange    │       │ extra_data  │              │          │
│ api_key     │       └─────────────┘              │          │
│ api_secret  │                                    │          │
└─────────────┘                                    │          │
                                                   │          │
┌─────────────┐       ┌─────────────────┐          │          │
│   balance   │       │  daily_metrics  │          │          │
├─────────────┤       ├─────────────────┤          │          │
│ id (PK)     │       │ id (PK)         │          │          │
│ user_id     │◄──────┤ user_id         │◄─────────┴──────────┘
│ exchange    │       │ date            │
│ amount      │       │ exchange        │
│ available   │       │ total_trades    │
│ used_margin │       │ total_pnl       │
│ unrealized  │       │ win_rate        │
└─────────────┘       │ profit_factor   │
                      └─────────────────┘

┌──────────────────┐  ┌───────────────────┐  ┌──────────────────┐
│position_snapshots│  │strategy_performance│  │ drawdown_records │
├──────────────────┤  ├───────────────────┤  ├──────────────────┤
│ id (PK)          │  │ id (PK)           │  │ id (PK)          │
│ user_id          │  │ user_id           │  │ user_id          │
│ exchange         │  │ strategy          │  │ exchange         │
│ pair             │  │ exchange          │  │ start_date       │
│ position_size    │  │ total_trades      │  │ end_date         │
│ entry_price      │  │ total_pnl         │  │ peak_balance     │
│ mark_price       │  │ win_rate          │  │ trough_balance   │
│ unrealized_pnl   │  │ max_drawdown      │  │ drawdown_pct     │
└──────────────────┘  └───────────────────┘  └──────────────────┘
```

### Table Descriptions

**users**: User accounts and authentication
**trades**: Individual trade records with full P&L tracking
**threads**: Active strategy threads
**keys**: Encrypted exchange API credentials
**balance**: Account balance snapshots
**daily_metrics**: Daily aggregated performance statistics
**position_snapshots**: Hourly position state for heatmap
**strategy_performance**: Per-strategy performance metrics
**drawdown_records**: Drawdown period tracking

## Troubleshooting

### Common Issues

#### Application won't start
```bash
# Check Python version
python --version  # Should be 3.13+

# Verify dependencies
uv sync

# Check database permissions
ls -la data/db/
```

#### Database locked errors
SQLite doesn't support concurrent writes. Ensure:
- Only one process accesses the database
- Use PostgreSQL for multi-instance deployments

#### WebSocket connection issues
- Check firewall settings (port 8000)
- Verify JWT token is valid
- Check CORS configuration

#### Strategy upload fails
- Ensure ZIP contains `main.py` and `config.json`
- Verify JSON syntax in config.json
- Check file permissions on threads directory

### Logs

**Docker:**
```bash
docker-compose logs -f aosiconn
```

**Systemd:**
```bash
sudo journalctl -u aosiconn -f
```

**Manual:**
```bash
tail -f data/logs/aosiconn.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please use the GitHub issue tracker.
