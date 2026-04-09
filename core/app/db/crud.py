from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from . import models, schemas
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


# user CRUD
def get_user(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_all_users(db: Session):
    return db.query(models.User).all()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        name=user.name, username=user.username, password=user.password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# key CRUD
def get_key(db: Session, user_id: int, exchange: str):
    return (
        db.query(models.Keys)
        .filter(models.Keys.user_id == user_id, models.Keys.exchange == exchange)
        .first()
    )


def get_keys(db: Session, user_id: int):
    return db.query(models.Keys).filter(models.Keys.user_id == user_id).all()


def modify_key(db: Session, user_id: int, exchange: str, api_key: str, api_secret: str):
    key = (
        db.query(models.Keys)
        .filter(models.Keys.user_id == user_id, models.Keys.exchange == exchange)
        .first()
    )
    key.api_key = api_key
    key.api_secret = api_secret
    db.commit()
    db.refresh(key)
    return key


def create_key(db: Session, key: schemas.KeyBase, user_id):
    db_key = models.Keys(
        exchange=key.exchange,
        user_id=user_id,
        api_key=key.api_key,
        api_secret=key.api_secret,
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key


def delete_key(db: Session, user_id: int, exchange: str):
    key = (
        db.query(models.Keys)
        .filter(models.Keys.user_id == user_id, models.Keys.exchange == exchange)
        .first()
    )
    db.delete(key)
    db.commit()
    return key


# trade CRUD
def get_all_trade(db: Session, user_id: int):
    return db.query(models.Trades).filter(models.Trades.user_id == user_id).all()


def get_trade_by_pair(db: Session, user_id: int, pair: str):
    return (
        db.query(models.Trades)
        .filter(models.Trades.user_id == user_id, models.Trades.pair == pair)
        .all()
    )


def get_trade_by_id(db: Session, trade_id: int):
    return db.query(models.Trades).filter(models.Trades.id == trade_id).first()


def get_trades_by_strategy(db: Session, user_id: int, strategy: str, limit: int = 100):
    return (
        db.query(models.Trades)
        .filter(models.Trades.user_id == user_id, models.Trades.strategy == strategy)
        .order_by(desc(models.Trades.entry_time))
        .limit(limit)
        .all()
    )


def get_closed_trades(
    db: Session, user_id: int, days: int = 30, exchange: str | None = None
):
    # Use naive UTC datetime to match what is stored by datetime.utcnow()
    start_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(models.Trades).filter(
        models.Trades.user_id == user_id,
        models.Trades.status == "closed",
        models.Trades.exit_time >= start_date,
    )
    if exchange is not None:
        query = query.filter(models.Trades.exchange == exchange)
    return query.order_by(desc(models.Trades.exit_time)).all()


def create_trade(db: Session, trade: schemas.Trades):
    add_trade = models.Trades(
        user_id=trade.user_id,
        exchange=trade.exchange,
        pair=trade.pair,
        qty=trade.qty,
        leverage=trade.leverage,
        action=trade.action,
        result=trade.result,
        strategy=trade.strategy,
        entry=trade.entry,
        profit=trade.profit,
        loss=trade.loss,
    )
    db.add(add_trade)
    db.commit()
    db.refresh(add_trade)
    return add_trade


def create_trade_extended(
    db: Session,
    user_id: int,
    trade_data: schemas.TradeCreate,
    entry_fee: float = 0.0,
    slippage: float = 0.0,
    metadata: Optional[dict] = None,
) -> models.Trades:
    """Create a new trade with extended fields"""
    db_trade = models.Trades(
        user_id=user_id,
        exchange=trade_data.exchange,
        pair=trade_data.pair,
        qty=trade_data.qty,
        leverage=trade_data.leverage,
        action=trade_data.action,
        strategy=trade_data.strategy,
        entry_price=trade_data.entry_price,
        stop_loss=trade_data.stop_loss,
        take_profit=trade_data.take_profit,
        entry_time=datetime.utcnow(),
        entry_fee=entry_fee,
        total_fees=entry_fee,
        slippage=slippage,
        status="open",
        extra_data=metadata,
    )

    # Calculate risk/reward ratio if both SL and TP are set
    if trade_data.stop_loss and trade_data.take_profit:
        risk = abs(trade_data.entry_price - trade_data.stop_loss)
        reward = abs(trade_data.take_profit - trade_data.entry_price)
        if risk > 0:
            db_trade.risk_reward_ratio = reward / risk

    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade


def close_trade(
    db: Session, trade_id: int, close_data: schemas.TradeClose
) -> Optional[models.Trades]:
    """Close an open trade with exit details"""
    trade = (
        db.query(models.Trades)
        .filter(models.Trades.id == trade_id, models.Trades.status == "open")
        .first()
    )

    if not trade:
        return None

    trade.exit_price = close_data.exit_price
    trade.exit_time = datetime.utcnow()
    trade.exit_fee = close_data.exit_fee
    trade.total_fees = (trade.entry_fee or 0.0) + (close_data.exit_fee or 0.0)
    trade.status = "closed"

    # Calculate duration
    if trade.entry_time:
        trade.duration_seconds = int(
            (trade.exit_time - trade.entry_time).total_seconds()
        )

    # P&L is based on filled size, not leverage. Leverage only changes margin used.
    leverage = trade.leverage if trade.leverage and trade.leverage > 0 else 1
    qty = trade.qty if trade.qty else 0.0
    if trade.action == 1:  # Buy/Long
        trade.pnl_abs = (
            (trade.exit_price - trade.entry_price) * qty
        ) - trade.total_fees
    else:  # Sell/Short
        trade.pnl_abs = (
            (trade.entry_price - trade.exit_price) * qty
        ) - trade.total_fees

    # Calculate percentage P&L against margin used (not full notional)
    # margin = notional / leverage  →  pnl_pct = pnl_abs / margin * 100
    margin_used = (trade.entry_price * qty) / leverage
    if margin_used > 0:
        trade.pnl_pct = (trade.pnl_abs / margin_used) * 100
    else:
        trade.pnl_pct = 0.0

    # Determine result (win/loss)
    if trade.pnl_abs > 0:
        trade.result = 1  # Win
    elif trade.pnl_abs < 0:
        trade.result = -1  # Loss
    else:
        trade.result = 0  # Breakeven

    db.commit()
    db.refresh(trade)
    return trade


def update_trade_result(
    db: Session, user_id: int, pair: str, exchange: str, price: float
):
    trade = (
        db.query(models.Trades)
        .filter(
            models.Trades.user_id == user_id,
            models.Trades.pair == pair,
            models.Trades.exchange == exchange,
        )
        .order_by(models.Trades.id.desc())
        .first()
    )

    if trade is None:
        logger.warning(
            f"update_trade_result: no trade found for user={user_id} pair={pair} exchange={exchange}"
        )
        return None

    if trade.entry_price is None:
        logger.warning(f"update_trade_result: trade {trade.id} has no entry_price")
        return trade

    if trade.action > 0:  # Long
        trade.result = 1 if price > trade.entry_price else -1
    else:  # Short
        trade.result = 1 if price < trade.entry_price else -1

    db.commit()
    db.refresh(trade)
    return trade


# thread CRUD
def create_thread(
    db: Session,
    user_id: int,
    pair: str,
    exchange: str,
    qty: float,
    leverage: int,
    message: str,
    strategy: str,
):
    db_thread = models.Threads(
        user_id=user_id,
        pair=pair,
        exchange=exchange,
        qty=qty,
        leverage=leverage,
        message=message,
        strategy=strategy,
        status="running",
        last_heartbeat=int(datetime.now().timestamp()),
    )
    db.add(db_thread)
    db.commit()
    db.refresh(db_thread)
    return db_thread


def get_thread(db: Session, thread_id: int):
    return db.query(models.Threads).filter(models.Threads.id == thread_id).first()


def get_threads(db: Session, user_id: int):
    return db.query(models.Threads).filter(models.Threads.user_id == user_id).all()


def get_all_threads(db: Session):
    return db.query(models.Threads).all()


def update_thread(db: Session, thread: schemas.Thread):
    db.commit()
    db.refresh(thread)
    return thread


def update_thread_status(db: Session, thread_id: int, status: str):
    thread = db.query(models.Threads).filter(models.Threads.id == thread_id).first()
    thread.status = status
    db.commit()
    db.refresh(thread)
    return thread


def update_thread_heartbeat(db: Session, thread_id: int):
    thread = db.query(models.Threads).filter(models.Threads.id == thread_id).first()
    thread.last_heartbeat = int(datetime.now().timestamp())
    db.commit()
    db.refresh(thread)
    return thread


def delete_thread(db: Session, thread_id: int):
    thread = db.query(models.Threads).filter(models.Threads.id == thread_id).first()
    db.delete(thread)
    db.commit()
    return thread


# balance crud
def update_balance(
    db: Session,
    user_id: int,
    exchange: str,
    amount: float,
    available: Optional[float] = None,
    used_margin: Optional[float] = None,
    unrealized_pnl: Optional[float] = None,
):
    # Use a single UTC "now" for all comparisons in this call
    now_utc = datetime.now(timezone.utc)
    today_utc = now_utc.date()
    now_ts = int(now_utc.timestamp())

    last_balance = (
        db.query(models.Balance)
        .filter(models.Balance.user_id == user_id, models.Balance.exchange == exchange)
        .order_by(models.Balance.timestamp.desc())
        .first()
    )

    if last_balance:
        # Convert stored Unix timestamp to UTC date for comparison
        last_date = datetime.fromtimestamp(
            last_balance.timestamp, tz=timezone.utc
        ).date()

        if last_date == today_utc:
            # Same UTC day — update in-place (one record per day per exchange)
            last_balance.amount = amount
            last_balance.timestamp = now_ts
            if available is not None:
                last_balance.available = available
            if used_margin is not None:
                last_balance.used_margin = used_margin
            if unrealized_pnl is not None:
                last_balance.unrealized_pnl = unrealized_pnl
            db.commit()
            db.refresh(last_balance)
            return last_balance

    # New day (or first record) — insert a fresh row
    new_balance = models.Balance(
        user_id=user_id,
        exchange=exchange,
        amount=amount,
        timestamp=now_ts,
        available=available,
        used_margin=used_margin,
        unrealized_pnl=unrealized_pnl,
    )

    db.add(new_balance)
    db.commit()
    db.refresh(new_balance)
    return new_balance


def get_balance(db: Session, user_id: int, exchange: str, days: int = 30):
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    query = db.query(models.Balance).filter(
        models.Balance.user_id == user_id,
        models.Balance.exchange == exchange,
        models.Balance.timestamp >= int(start_date.timestamp()),
    )

    bal = query.order_by(models.Balance.timestamp.desc()).all()
    return bal


def get_latest_balance(db: Session, user_id: int, exchange: str):
    return (
        db.query(models.Balance)
        .filter(models.Balance.user_id == user_id, models.Balance.exchange == exchange)
        .order_by(desc(models.Balance.timestamp))
        .first()
    )


# Daily Metrics CRUD
def get_or_create_daily_metrics(
    db: Session, user_id: int, exchange: str, date: datetime
) -> models.DailyMetrics:
    """Get existing daily metrics or create new one"""
    metrics = (
        db.query(models.DailyMetrics)
        .filter(
            models.DailyMetrics.user_id == user_id,
            models.DailyMetrics.exchange == exchange,
            models.DailyMetrics.date == date,
        )
        .first()
    )

    if not metrics:
        metrics = models.DailyMetrics(user_id=user_id, exchange=exchange, date=date)
        db.add(metrics)
        db.commit()
        db.refresh(metrics)

    return metrics


def update_daily_metrics(db: Session, metrics: models.DailyMetrics):
    db.commit()
    db.refresh(metrics)
    return metrics


def get_daily_metrics(
    db: Session, user_id: int, exchange: str, days: int = 30
) -> List[models.DailyMetrics]:
    start_date = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(models.DailyMetrics)
        .filter(
            models.DailyMetrics.user_id == user_id,
            models.DailyMetrics.exchange == exchange,
            models.DailyMetrics.date >= start_date,
        )
        .order_by(models.DailyMetrics.date)
        .all()
    )


# Position Snapshot CRUD
def create_position_snapshot(
    db: Session,
    user_id: int,
    exchange: str,
    pair: str,
    position_size: float,
    entry_price: float,
    mark_price: float,
    unrealized_pnl: float,
    margin_used: float,
    leverage: int,
    position_value: float,
    liquidation_price: Optional[float] = None,
    margin_ratio: Optional[float] = None,
) -> models.PositionSnapshot:
    snapshot = models.PositionSnapshot(
        user_id=user_id,
        exchange=exchange,
        pair=pair,
        position_size=position_size,
        entry_price=entry_price,
        mark_price=mark_price,
        unrealized_pnl=unrealized_pnl,
        margin_used=margin_used,
        leverage=leverage,
        position_value=position_value,
        liquidation_price=liquidation_price,
        margin_ratio=margin_ratio,
        timestamp=datetime.utcnow(),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_position_snapshots(
    db: Session,
    user_id: int,
    exchange: str,
    pair: Optional[str] = None,
    hours: int = 24,
) -> List[models.PositionSnapshot]:
    start_time = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(models.PositionSnapshot).filter(
        models.PositionSnapshot.user_id == user_id,
        models.PositionSnapshot.exchange == exchange,
        models.PositionSnapshot.timestamp >= start_time,
    )

    if pair:
        query = query.filter(models.PositionSnapshot.pair == pair)

    return query.order_by(models.PositionSnapshot.timestamp).all()


def get_latest_position_snapshot(
    db: Session, user_id: int, exchange: str, pair: str
) -> Optional[models.PositionSnapshot]:
    return (
        db.query(models.PositionSnapshot)
        .filter(
            models.PositionSnapshot.user_id == user_id,
            models.PositionSnapshot.exchange == exchange,
            models.PositionSnapshot.pair == pair,
        )
        .order_by(desc(models.PositionSnapshot.timestamp))
        .first()
    )


# Strategy Performance CRUD
def get_or_create_strategy_performance(
    db: Session, user_id: int, strategy: str, exchange: str
) -> models.StrategyPerformance:
    performance = (
        db.query(models.StrategyPerformance)
        .filter(
            models.StrategyPerformance.user_id == user_id,
            models.StrategyPerformance.strategy == strategy,
            models.StrategyPerformance.exchange == exchange,
        )
        .first()
    )

    if not performance:
        performance = models.StrategyPerformance(
            user_id=user_id, strategy=strategy, exchange=exchange
        )
        db.add(performance)
        db.commit()
        db.refresh(performance)

    return performance


def update_strategy_performance(db: Session, performance: models.StrategyPerformance):
    performance.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(performance)
    return performance


def get_strategy_performance(
    db: Session, user_id: int, exchange: str
) -> List[models.StrategyPerformance]:
    return (
        db.query(models.StrategyPerformance)
        .filter(
            models.StrategyPerformance.user_id == user_id,
            models.StrategyPerformance.exchange == exchange,
        )
        .order_by(desc(models.StrategyPerformance.total_pnl))
        .all()
    )


# Drawdown Records CRUD
def create_drawdown_record(
    db: Session, user_id: int, exchange: str, peak_balance: float
) -> models.DrawdownRecord:
    record = models.DrawdownRecord(
        user_id=user_id,
        exchange=exchange,
        peak_balance=peak_balance,
        trough_balance=peak_balance,
        drawdown_amount=0.0,
        drawdown_pct=0.0,
        recovered=False,
        start_date=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_active_drawdown(
    db: Session, user_id: int, exchange: str
) -> Optional[models.DrawdownRecord]:
    return (
        db.query(models.DrawdownRecord)
        .filter(
            models.DrawdownRecord.user_id == user_id,
            models.DrawdownRecord.exchange == exchange,
            models.DrawdownRecord.recovered == False,
        )
        .order_by(desc(models.DrawdownRecord.start_date))
        .first()
    )


def recompute_trade_metrics(
    db: Session, exchange: str | None = None, strategy: str | None = None
) -> int:
    """Recalculate trade P&L fields for existing closed trades after formula fixes."""
    query = db.query(models.Trades).filter(
        models.Trades.status == "closed",
        models.Trades.entry_price.isnot(None),
        models.Trades.exit_price.isnot(None),
    )
    if exchange is not None:
        query = query.filter(models.Trades.exchange == exchange)
    if strategy is not None:
        query = query.filter(models.Trades.strategy == strategy)

    trades = query.all()
    updated = 0
    for trade in trades:
        qty = trade.qty or 0.0
        leverage = trade.leverage if trade.leverage and trade.leverage > 0 else 1
        total_fees = trade.total_fees or 0.0

        if trade.action == 1:
            trade.pnl_abs = ((trade.exit_price - trade.entry_price) * qty) - total_fees
        else:
            trade.pnl_abs = ((trade.entry_price - trade.exit_price) * qty) - total_fees

        margin_used = (trade.entry_price * qty) / leverage
        trade.pnl_pct = (trade.pnl_abs / margin_used) * 100 if margin_used > 0 else 0.0

        if trade.pnl_abs > 0:
            trade.result = 1
        elif trade.pnl_abs < 0:
            trade.result = -1
        else:
            trade.result = 0

        if trade.entry_time and trade.exit_time:
            trade.duration_seconds = int(
                (trade.exit_time - trade.entry_time).total_seconds()
            )
        updated += 1

    if updated:
        db.commit()
    return updated


def update_drawdown(db: Session, record: models.DrawdownRecord, current_balance: float):
    """Update drawdown record with current balance"""
    if current_balance < record.trough_balance:
        record.trough_balance = current_balance
        record.drawdown_amount = record.peak_balance - current_balance
        if record.peak_balance > 0:
            record.drawdown_pct = (record.drawdown_amount / record.peak_balance) * 100

    if current_balance >= record.peak_balance:
        # Recovery
        record.recovered = True
        record.end_date = datetime.utcnow()
        if record.start_date:
            record.duration_days = (record.end_date - record.start_date).days

    db.commit()
    db.refresh(record)
    return record


def get_drawdown_history(
    db: Session, user_id: int, exchange: str, limit: int = 20
) -> List[models.DrawdownRecord]:
    return (
        db.query(models.DrawdownRecord)
        .filter(
            models.DrawdownRecord.user_id == user_id,
            models.DrawdownRecord.exchange == exchange,
        )
        .order_by(desc(models.DrawdownRecord.start_date))
        .limit(limit)
        .all()
    )
