from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Float,
    BigInteger,
    DateTime,
    JSON,
    Enum,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .database import Base


class TradeStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TradeAction(int, enum.Enum):
    BUY = 1
    SELL = -1


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    trades = relationship("Trades", back_populates="owner")
    keys = relationship("Keys", back_populates="owner")
    threads = relationship("Threads", back_populates="owner")
    balance = relationship("Balance", back_populates="owner")
    daily_metrics = relationship("DailyMetrics", back_populates="owner")


class Trades(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exchange = Column(String, index=True)
    pair = Column(String, index=True)
    qty = Column(Float)  # Changed to Float for fractional amounts
    leverage = Column(Integer)
    action = Column(Integer)  # 1 for buy, -1 for sell
    result = Column(Integer)  # 1 for win, -1 for loss, 0 for breakeven
    strategy = Column(String, index=True)

    # Entry/Exit details
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)

    # P&L tracking
    pnl_abs = Column(Float, default=0.0)  # Absolute P&L in USDC
    pnl_pct = Column(Float, default=0.0)  # Percentage P&L

    # Fees
    entry_fee = Column(Float, default=0.0)
    exit_fee = Column(Float, default=0.0)
    total_fees = Column(Float, default=0.0)

    # Risk management
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)

    # Trade status
    status = Column(String, default="open")  # open, closed, cancelled

    # Metadata
    duration_seconds = Column(Integer, nullable=True)  # Trade duration
    slippage = Column(Float, default=0.0)  # Entry slippage

    # Additional data
    extra_data = Column(JSON, nullable=True)  # For additional per-trade data

    owner = relationship("User", back_populates="trades")


class Keys(Base):
    __tablename__ = "keys"

    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    api_key = Column(String)
    api_secret = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="keys")


class Threads(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    pair = Column(String, index=True)
    qty = Column(Float)  # Changed to Float
    exchange = Column(String)
    leverage = Column(Integer)
    strategy = Column(String, index=True)
    message = Column(String)
    status = Column(String)
    last_heartbeat = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="threads")


class Balance(Base):
    __tablename__ = "balance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exchange = Column(String)
    amount = Column(Float)
    timestamp = Column(BigInteger)

    # Extended balance info
    available = Column(Float, nullable=True)
    used_margin = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, nullable=True)

    owner = relationship("User", back_populates="balance")


class DailyMetrics(Base):
    """Daily aggregated performance metrics"""

    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, index=True)  # Date (midnight UTC)
    exchange = Column(String, index=True)

    # Trade counts
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    breakeven_trades = Column(Integer, default=0)

    # P&L
    total_pnl = Column(Float, default=0.0)
    gross_profit = Column(Float, default=0.0)
    gross_loss = Column(Float, default=0.0)
    total_fees = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)

    # Performance ratios
    win_rate = Column(Float, default=0.0)  # Percentage
    profit_factor = Column(Float, default=0.0)

    # Averages
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    avg_trade = Column(Float, default=0.0)

    # Balance tracking
    starting_balance = Column(Float, nullable=True)
    ending_balance = Column(Float, nullable=True)

    # Streak tracking
    max_consecutive_wins = Column(Integer, default=0)
    max_consecutive_losses = Column(Integer, default=0)
    current_streak = Column(
        Integer, default=0
    )  # Positive for wins, negative for losses

    owner = relationship("User", back_populates="daily_metrics")


class PositionSnapshot(Base):
    """Hourly position snapshots for heatmap"""

    __tablename__ = "position_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exchange = Column(String)
    pair = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Position data
    position_size = Column(Float)  # Positive for long, negative for short
    entry_price = Column(Float)
    mark_price = Column(Float)
    unrealized_pnl = Column(Float)
    margin_used = Column(Float)
    leverage = Column(Integer)
    liquidation_price = Column(Float, nullable=True)

    # Risk metrics
    margin_ratio = Column(Float, nullable=True)  # Current margin ratio
    position_value = Column(Float)


class StrategyPerformance(Base):
    """Aggregated performance by strategy"""

    __tablename__ = "strategy_performance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    strategy = Column(String, index=True)
    exchange = Column(String, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Trade counts
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)

    # P&L
    total_pnl = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)

    # Streaks
    max_consecutive_wins = Column(Integer, default=0)
    max_consecutive_losses = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)

    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)

    # First/Last trade timestamps
    first_trade_at = Column(DateTime, nullable=True)
    last_trade_at = Column(DateTime, nullable=True)


class DrawdownRecord(Base):
    """Track drawdown periods for analysis"""

    __tablename__ = "drawdown_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exchange = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime, nullable=True)  # NULL if ongoing
    peak_balance = Column(Float)
    trough_balance = Column(Float)
    drawdown_amount = Column(Float)
    drawdown_pct = Column(Float)
    recovered = Column(Boolean, default=False)
    duration_days = Column(Integer, nullable=True)
