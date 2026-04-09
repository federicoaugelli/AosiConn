from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from auth.auth_bearer import JWTBearer
from utils.router_utils import get_user_id
from utils.metrics_service import metrics_calculator
from db.database import get_db
from db import crud, models
from db.schemas import (
    PerformanceSummary,
    DashboardData,
    EquityPoint,
    DailyMetrics,
    StrategyPerformance,
    DrawdownRecord,
    PositionSnapshot,
)

router = APIRouter()


@router.get("/performance", response_model=PerformanceSummary)
async def get_performance_summary(
    exchange: str = Query(default="hyperliquid", description="Exchange name"),
    days: int = Query(
        default=30, ge=1, le=365, description="Number of days to analyze"
    ),
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> PerformanceSummary:
    """Get comprehensive performance summary including P&L, win rate, drawdown, etc."""
    uid = get_user_id(user_id)
    return metrics_calculator.calculate_performance_summary(db, uid, exchange, days)


@router.get("/equity-curve")
async def get_equity_curve(
    exchange: str = Query(default="hyperliquid", description="Exchange name"),
    days: int = Query(default=90, ge=1, le=365, description="Number of days"),
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """Get equity curve data for charting"""
    uid = get_user_id(user_id)
    equity_curve = metrics_calculator.generate_equity_curve(db, uid, exchange, days)

    return [
        {
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "balance": e.balance,
            "daily_pnl": e.daily_pnl,
            "drawdown": e.drawdown,
            "drawdown_pct": e.drawdown_pct,
        }
        for e in equity_curve
    ]


@router.get("/daily-metrics")
async def get_daily_metrics(
    exchange: str = Query(default="hyperliquid", description="Exchange name"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """Get daily aggregated metrics"""
    uid = get_user_id(user_id)
    metrics = crud.get_daily_metrics(db, uid, exchange, days)

    return [
        {
            "date": m.date.isoformat() if m.date else None,
            "total_trades": m.total_trades,
            "winning_trades": m.winning_trades,
            "losing_trades": m.losing_trades,
            "breakeven_trades": m.breakeven_trades,
            "total_pnl": m.total_pnl,
            "net_pnl": m.net_pnl,
            "win_rate": m.win_rate,
            "profit_factor": m.profit_factor,
            "avg_win": m.avg_win,
            "avg_loss": m.avg_loss,
            "max_consecutive_wins": m.max_consecutive_wins,
            "max_consecutive_losses": m.max_consecutive_losses,
            "current_streak": m.current_streak,
        }
        for m in metrics
    ]


@router.get("/strategy-performance")
async def get_strategy_performance(
    exchange: str = Query(default="hyperliquid", description="Exchange name"),
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """Get performance metrics for each strategy"""
    uid = get_user_id(user_id)
    performances = crud.get_strategy_performance(db, uid, exchange)

    return [
        {
            "strategy": p.strategy,
            "total_trades": p.total_trades,
            "winning_trades": p.winning_trades,
            "losing_trades": p.losing_trades,
            "total_pnl": p.total_pnl,
            "win_rate": p.win_rate,
            "profit_factor": p.profit_factor,
            "avg_win": p.avg_win,
            "avg_loss": p.avg_loss,
            "max_consecutive_wins": p.max_consecutive_wins,
            "max_consecutive_losses": p.max_consecutive_losses,
            "current_streak": p.current_streak,
            "max_drawdown": p.max_drawdown,
            "max_drawdown_pct": p.max_drawdown_pct,
            "first_trade_at": p.first_trade_at.isoformat()
            if p.first_trade_at
            else None,
            "last_trade_at": p.last_trade_at.isoformat() if p.last_trade_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in performances
    ]


@router.get("/drawdowns")
async def get_drawdown_history(
    exchange: str = Query(default="hyperliquid", description="Exchange name"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of records"),
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """Get drawdown history"""
    uid = get_user_id(user_id)
    drawdowns = crud.get_drawdown_history(db, uid, exchange, limit)

    return [
        {
            "start_date": d.start_date.isoformat() if d.start_date else None,
            "end_date": d.end_date.isoformat() if d.end_date else None,
            "peak_balance": d.peak_balance,
            "trough_balance": d.trough_balance,
            "drawdown_amount": d.drawdown_amount,
            "drawdown_pct": d.drawdown_pct,
            "recovered": d.recovered,
            "duration_days": d.duration_days,
        }
        for d in drawdowns
    ]


@router.get("/position-heatmap")
async def get_position_heatmap(
    exchange: str = Query(default="hyperliquid", description="Exchange name"),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history"),
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """Get position heatmap data showing activity by pair"""
    uid = get_user_id(user_id)
    heatmap = metrics_calculator.calculate_position_heatmap(db, uid, exchange, hours)
    return heatmap


@router.get("/returns")
async def get_returns_by_period(
    exchange: str = Query(default="hyperliquid", description="Exchange name"),
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> Dict:
    """Get returns grouped by daily, weekly, and monthly periods"""
    uid = get_user_id(user_id)
    returns = metrics_calculator.calculate_returns_by_period(db, uid, exchange)
    return returns


@router.get("/trades")
async def get_trade_history(
    exchange: str = Query(default="hyperliquid", description="Exchange name"),
    pair: Optional[str] = Query(default=None, description="Filter by trading pair"),
    strategy: Optional[str] = Query(default=None, description="Filter by strategy"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max results"),
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """Get detailed trade history with P&L information"""
    uid = get_user_id(user_id)

    # Build query
    query = db.query(models.Trades).filter(
        models.Trades.user_id == uid, models.Trades.exchange == exchange
    )

    if pair:
        query = query.filter(models.Trades.pair == pair)

    if strategy:
        query = query.filter(models.Trades.strategy == strategy)

    if days:
        start_date = datetime.now(timezone.utc) - __import__("datetime").timedelta(
            days=days
        )
        query = query.filter(models.Trades.entry_time >= start_date)

    trades = query.order_by(models.Trades.entry_time.desc()).limit(limit).all()

    return [
        {
            "id": t.id,
            "pair": t.pair,
            "strategy": t.strategy,
            "action": "buy" if t.action == 1 else "sell",
            "qty": t.qty,
            "leverage": t.leverage,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "entry_time": t.entry_time.isoformat() if t.entry_time else None,
            "exit_time": t.exit_time.isoformat() if t.exit_time else None,
            "pnl_abs": t.pnl_abs,
            "pnl_pct": t.pnl_pct,
            "total_fees": t.total_fees,
            "duration_seconds": t.duration_seconds,
            "result": "win"
            if t.result == 1
            else "loss"
            if t.result == -1
            else "breakeven",
            "status": t.status,
        }
        for t in trades
    ]


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(
    exchange: str = Query(default="hyperliquid", description="Exchange name"),
    days: int = Query(default=30, ge=1, le=90, description="Number of days"),
    user_id: str = Depends(JWTBearer()),
    db: Session = Depends(get_db),
) -> Dict:
    """Get all dashboard data in a single request"""
    uid = get_user_id(user_id)

    # Get all data
    performance = metrics_calculator.calculate_performance_summary(
        db, uid, exchange, days
    )
    equity_curve = metrics_calculator.generate_equity_curve(db, uid, exchange, days)
    daily_metrics = crud.get_daily_metrics(db, uid, exchange, days)
    strategy_perf = crud.get_strategy_performance(db, uid, exchange)
    recent_trades = crud.get_closed_trades(db, uid, days)[:20]  # Last 20 trades

    # Get active positions (last snapshot for each pair)
    positions = crud.get_position_snapshots(db, uid, exchange, hours=1)
    latest_positions = {}
    for pos in positions:
        if (
            pos.pair not in latest_positions
            or pos.timestamp > latest_positions[pos.pair].timestamp
        ):
            latest_positions[pos.pair] = pos

    return {
        "performance_summary": performance,
        "equity_curve": [
            {
                "timestamp": e.timestamp,
                "balance": e.balance,
                "daily_pnl": e.daily_pnl,
                "drawdown": e.drawdown,
                "drawdown_pct": e.drawdown_pct,
            }
            for e in equity_curve
        ],
        "recent_trades": [
            {
                "id": t.id,
                "pair": t.pair,
                "strategy": t.strategy,
                "action": t.action,
                "qty": t.qty,
                "leverage": t.leverage,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "pnl_abs": t.pnl_abs,
                "pnl_pct": t.pnl_pct,
                "result": t.result,
                "status": t.status,
            }
            for t in recent_trades
        ],
        "active_positions": [
            {
                "pair": p.pair,
                "position_size": p.position_size,
                "entry_price": p.entry_price,
                "mark_price": p.mark_price,
                "unrealized_pnl": p.unrealized_pnl,
                "margin_used": p.margin_used,
                "leverage": p.leverage,
                "timestamp": p.timestamp,
            }
            for p in latest_positions.values()
        ],
        "strategy_performance": [
            {
                "strategy": p.strategy,
                "total_trades": p.total_trades,
                "winning_trades": p.winning_trades,
                "losing_trades": p.losing_trades,
                "total_pnl": p.total_pnl,
                "win_rate": p.win_rate,
                "profit_factor": p.profit_factor,
                "avg_win": p.avg_win,
                "avg_loss": p.avg_loss,
                "max_drawdown_pct": p.max_drawdown_pct,
                "current_streak": p.current_streak,
            }
            for p in strategy_perf
        ],
        "daily_metrics": [
            {
                "date": m.date,
                "total_trades": m.total_trades,
                "winning_trades": m.winning_trades,
                "losing_trades": m.losing_trades,
                "total_pnl": m.total_pnl,
                "net_pnl": m.net_pnl,
                "win_rate": m.win_rate,
            }
            for m in daily_metrics
        ],
    }
