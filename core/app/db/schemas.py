from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TradeAction(int, Enum):
    BUY = 1
    SELL = -1


# Base schemas
class UserBase(BaseModel):
    name: str
    username: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# API Key schemas
class KeyBase(BaseModel):
    exchange: str
    api_key: str
    api_secret: str


class KeyCreate(KeyBase):
    pass


class Key(KeyBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Trade schemas - maintaining backward compatibility
class Trades(BaseModel):
    user_id: int
    exchange: str
    pair: str
    qty: float
    leverage: int
    action: int
    result: int
    strategy: str
    entry: float
    profit: float
    loss: float

    class Config:
        from_attributes = True


class TradeBase(BaseModel):
    exchange: str
    pair: str
    qty: float
    leverage: int
    action: int
    strategy: str
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class TradeCreate(TradeBase):
    pass


class Trade(TradeBase):
    id: int
    user_id: int
    result: Optional[int] = None
    exit_price: Optional[float] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    pnl_abs: float
    pnl_pct: float
    entry_fee: float
    exit_fee: float
    total_fees: float
    risk_reward_ratio: Optional[float] = None
    status: str
    duration_seconds: Optional[int] = None
    slippage: float
    extra_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class TradeClose(BaseModel):
    exit_price: float
    exit_fee: Optional[float] = 0.0


# Thread schemas - maintaining backward compatibility
class Thread(BaseModel):
    id: int
    user_id: int
    pair: str
    qty: float  # Changed from int to float
    leverage: int
    strategy: str
    status: str
    last_heartbeat: int

    class Config:
        from_attributes = True


class ThreadBase(BaseModel):
    pair: str
    exchange: str
    qty: float
    leverage: int
    strategy: str
    message: str


class ThreadCreate(ThreadBase):
    pass


# Strategy schemas
class insert_strategy(BaseModel):
    strategy: str
    pair: str
    exchange: str = "hyperliquid"
    qty: float  # float to support fractional amounts (e.g. 0.001 BTC)
    leverage: int
    message: str = ""


class update_strategy(BaseModel):
    thread_id: int
    pair: Optional[str] = None
    qty: Optional[float] = None  # float to support fractional amounts
    leverage: Optional[int] = None
    message: Optional[str] = None


# Balance schemas - maintaining backward compatibility
class Balance(BaseModel):
    id: int
    user_id: int
    exchange: str
    amount: float
    timestamp: int

    class Config:
        from_attributes: True


class BalanceBase(BaseModel):
    exchange: str
    amount: float


class BalanceCreate(BalanceBase):
    pass


class BalanceDetail(BalanceBase):
    id: int
    user_id: int
    timestamp: int
    available: Optional[float] = None
    used_margin: Optional[float] = None
    unrealized_pnl: Optional[float] = None

    class Config:
        from_attributes = True


# Daily Metrics schemas
class DailyMetrics(BaseModel):
    id: int
    user_id: int
    date: datetime
    exchange: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    total_pnl: float
    gross_profit: float
    gross_loss: float
    total_fees: float
    net_pnl: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    avg_trade: float
    starting_balance: Optional[float] = None
    ending_balance: Optional[float] = None
    max_consecutive_wins: int
    max_consecutive_losses: int
    current_streak: int

    class Config:
        from_attributes = True


# Strategy Performance schemas
class StrategyPerformance(BaseModel):
    id: int
    user_id: int
    strategy: str
    exchange: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    current_streak: int
    max_drawdown: float
    max_drawdown_pct: float
    first_trade_at: Optional[datetime] = None
    last_trade_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# Position Snapshot schemas
class PositionSnapshot(BaseModel):
    id: int
    user_id: int
    exchange: str
    pair: str
    timestamp: datetime
    position_size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    margin_used: float
    leverage: int
    liquidation_price: Optional[float] = None
    margin_ratio: Optional[float] = None
    position_value: float

    class Config:
        from_attributes = True


# Drawdown schemas
class DrawdownRecord(BaseModel):
    id: int
    user_id: int
    exchange: str
    start_date: datetime
    end_date: Optional[datetime] = None
    peak_balance: float
    trough_balance: float
    drawdown_amount: float
    drawdown_pct: float
    recovered: bool
    duration_days: Optional[int] = None

    class Config:
        from_attributes = True


# Performance Summary schema
class PerformanceSummary(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate: float
    profit_factor: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    avg_trade: float
    max_drawdown: float
    max_drawdown_pct: float
    current_streak: int
    max_consecutive_wins: int
    max_consecutive_losses: int
    sharpe_ratio: Optional[float] = None


# Equity Curve Point
class EquityPoint(BaseModel):
    timestamp: datetime
    balance: float
    daily_pnl: float
    drawdown: float
    drawdown_pct: float


# Position Heatmap Data
class PositionHeatmapData(BaseModel):
    pair: str
    timestamp: datetime
    position_size: float
    unrealized_pnl: float
    margin_used: float


# Dashboard Data
class DashboardData(BaseModel):
    performance_summary: PerformanceSummary
    equity_curve: List[EquityPoint]
    recent_trades: List[Trade]
    active_positions: List[PositionSnapshot]
    strategy_performance: List[StrategyPerformance]
    daily_metrics: List[DailyMetrics]


# WebSocket Message schemas
class WSMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TradeUpdate(BaseModel):
    trade: Trade
    message_type: str = "trade_update"


class PositionUpdate(BaseModel):
    position: PositionSnapshot
    message_type: str = "position_update"


class BalanceUpdate(BaseModel):
    balance: BalanceDetail
    message_type: str = "balance_update"


class MetricsUpdate(BaseModel):
    metrics: DailyMetrics
    message_type: str = "metrics_update"
