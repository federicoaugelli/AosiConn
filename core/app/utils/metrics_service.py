"""
Metrics calculation service for trading performance analytics.
Calculates comprehensive trading metrics including P&L, drawdowns, streaks, etc.
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import math
import logging

from db import crud, models
from db.schemas import PerformanceSummary, EquityPoint, DailyMetrics

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculator for comprehensive trading metrics"""

    @staticmethod
    def calculate_trade_duration(trade: models.Trades) -> Optional[int]:
        """Calculate trade duration in seconds"""
        if trade.exit_time and trade.entry_time:
            return int((trade.exit_time - trade.entry_time).total_seconds())
        return None

    @staticmethod
    def calculate_pnl(trade: models.Trades) -> Tuple[float, float]:
        """Calculate net absolute and percentage P&L for a trade."""
        if not trade.exit_price or not trade.entry_price:
            return 0.0, 0.0

        leverage = trade.leverage if trade.leverage and trade.leverage > 0 else 1
        qty = trade.qty if trade.qty else 0.0

        if trade.action == 1:  # Buy/Long
            pnl_abs = (trade.exit_price - trade.entry_price) * qty
        else:  # Sell/Short
            pnl_abs = (trade.entry_price - trade.exit_price) * qty

        if trade.total_fees:
            pnl_abs -= trade.total_fees

        margin_used = (trade.entry_price * qty) / leverage
        if margin_used > 0:
            pnl_pct = (pnl_abs / margin_used) * 100
        else:
            pnl_pct = 0.0

        return pnl_abs, pnl_pct

    @staticmethod
    def calculate_win_rate(trades: List[models.Trades]) -> float:
        """Calculate win rate percentage"""
        if not trades:
            return 0.0

        winning_trades = sum(1 for t in trades if t.result == 1)
        return (winning_trades / len(trades)) * 100

    @staticmethod
    def calculate_profit_factor(trades: List[models.Trades]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = sum(t.pnl_abs for t in trades if t.pnl_abs > 0)
        gross_loss = abs(sum(t.pnl_abs for t in trades if t.pnl_abs < 0))

        if gross_loss == 0:
            return gross_profit if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    @staticmethod
    def calculate_average_trades(trades: List[models.Trades]) -> Dict[str, float]:
        """Calculate average win, loss, and overall trade"""
        winning_trades = [t.pnl_abs for t in trades if t.pnl_abs > 0]
        losing_trades = [t.pnl_abs for t in trades if t.pnl_abs < 0]
        all_pnl = [t.pnl_abs for t in trades]

        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0.0
        avg_trade = sum(all_pnl) / len(all_pnl) if all_pnl else 0.0

        return {"avg_win": avg_win, "avg_loss": avg_loss, "avg_trade": avg_trade}

    @staticmethod
    def calculate_streaks(trades: List[models.Trades]) -> Dict[str, int]:
        """Calculate consecutive win/loss streaks"""
        if not trades:
            return {
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "current_streak": 0,
            }

        max_wins = 0
        max_losses = 0
        current_streak = 0
        current_wins = 0
        current_losses = 0

        for trade in trades:
            if trade.result == 1:  # Win
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif trade.result == -1:  # Loss
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        # Current streak
        if current_wins > 0:
            current_streak = current_wins
        elif current_losses > 0:
            current_streak = -current_losses

        return {
            "max_consecutive_wins": max_wins,
            "max_consecutive_losses": max_losses,
            "current_streak": current_streak,
        }

    @staticmethod
    def calculate_drawdown(equity_curve: List[Dict]) -> Dict[str, float]:
        """Calculate maximum drawdown from equity curve"""
        if not equity_curve:
            return {"max_drawdown": 0.0, "max_drawdown_pct": 0.0}

        peak = equity_curve[0]["balance"]
        max_drawdown = 0.0
        max_drawdown_pct = 0.0

        for point in equity_curve:
            balance = point["balance"]
            if balance > peak:
                peak = balance

            drawdown = peak - balance
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0.0

            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct

        return {"max_drawdown": max_drawdown, "max_drawdown_pct": max_drawdown_pct}

    @staticmethod
    def calculate_sharpe_ratio(
        returns: List[float], risk_free_rate: float = 0.0
    ) -> Optional[float]:
        """Calculate Sharpe ratio from daily returns"""
        if len(returns) < 2:
            return None

        excess_returns = [r - risk_free_rate for r in returns]
        avg_return = sum(excess_returns) / len(excess_returns)

        # Calculate standard deviation
        variance = sum((r - avg_return) ** 2 for r in excess_returns) / (
            len(excess_returns) - 1
        )
        std_dev = math.sqrt(variance) if variance > 0 else 0.0

        if std_dev == 0:
            return None

        # Annualized Sharpe (assuming daily returns)
        return (avg_return / std_dev) * math.sqrt(365)

    @staticmethod
    def calculate_expectancy(trades: List[models.Trades]) -> float:
        """Calculate trading expectancy: (Win% * Avg Win) - (Loss% * Avg Loss)"""
        if not trades:
            return 0.0

        win_rate = MetricsCalculator.calculate_win_rate(trades) / 100
        loss_rate = 1 - win_rate

        avg_pnl = MetricsCalculator.calculate_average_trades(trades)

        expectancy = (win_rate * avg_pnl["avg_win"]) + (loss_rate * avg_pnl["avg_loss"])
        return expectancy

    @classmethod
    def generate_equity_curve(
        cls, db: Session, user_id: int, exchange: str, days: int = 90
    ) -> List[EquityPoint]:
        """Generate equity curve from balance history and closed trades"""
        # Get daily balance data
        balances = crud.get_balance(db, user_id, exchange, days)

        if not balances:
            return []

        # Sort by timestamp
        balances.sort(key=lambda x: x.timestamp)

        equity_points = []
        peak = balances[0].amount if balances else 0.0

        for balance in balances:
            balance_value = balance.amount
            timestamp = datetime.fromtimestamp(balance.timestamp, tz=timezone.utc)

            # Calculate drawdown
            if balance_value > peak:
                peak = balance_value

            drawdown = peak - balance_value
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0.0

            equity_points.append(
                EquityPoint(
                    timestamp=timestamp,
                    balance=balance_value,
                    daily_pnl=0.0,  # Will be calculated below
                    drawdown=drawdown,
                    drawdown_pct=drawdown_pct,
                )
            )

        # Calculate daily P&L
        for i in range(1, len(equity_points)):
            equity_points[i].daily_pnl = (
                equity_points[i].balance - equity_points[i - 1].balance
            )

        return equity_points

    @classmethod
    def calculate_performance_summary(
        cls, db: Session, user_id: int, exchange: str, days: int = 30
    ) -> PerformanceSummary:
        """Calculate comprehensive performance summary"""
        # Get closed trades
        trades = crud.get_closed_trades(db, user_id, days, exchange)

        if not trades:
            return PerformanceSummary(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                total_pnl=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                avg_trade=0.0,
                max_drawdown=0.0,
                max_drawdown_pct=0.0,
                current_streak=0,
                max_consecutive_wins=0,
                max_consecutive_losses=0,
                sharpe_ratio=None,
            )

        # Basic counts
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.result == 1)
        losing_trades = sum(1 for t in trades if t.result == -1)
        breakeven_trades = sum(1 for t in trades if t.result == 0)

        # P&L
        total_pnl = sum(t.pnl_abs for t in trades)

        # Averages
        avg_pnl = cls.calculate_average_trades(trades)

        # Win rate
        win_rate = cls.calculate_win_rate(trades)

        # Profit factor
        profit_factor = cls.calculate_profit_factor(trades)

        # Streaks
        streaks = cls.calculate_streaks(trades)

        # Drawdown from equity curve
        equity_curve = cls.generate_equity_curve(db, user_id, exchange, days)
        drawdown = cls.calculate_drawdown([e.model_dump() for e in equity_curve])

        # Sharpe ratio from daily returns
        daily_returns = [e.daily_pnl for e in equity_curve if e.daily_pnl != 0]
        sharpe = cls.calculate_sharpe_ratio(daily_returns)

        return PerformanceSummary(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            breakeven_trades=breakeven_trades,
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            total_pnl=round(total_pnl, 2),
            avg_win=round(avg_pnl["avg_win"], 2),
            avg_loss=round(avg_pnl["avg_loss"], 2),
            avg_trade=round(avg_pnl["avg_trade"], 2),
            max_drawdown=round(drawdown["max_drawdown"], 2),
            max_drawdown_pct=round(drawdown["max_drawdown_pct"], 2),
            current_streak=streaks["current_streak"],
            max_consecutive_wins=streaks["max_consecutive_wins"],
            max_consecutive_losses=streaks["max_consecutive_losses"],
            sharpe_ratio=round(sharpe, 2) if sharpe else None,
        )

    @classmethod
    def update_daily_metrics(
        cls, db: Session, user_id: int, exchange: str, date: datetime = None
    ):
        """Update daily metrics for a specific date"""
        # Always use naive UTC to match what is stored by datetime.utcnow()
        if not date:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif date.tzinfo is not None:
            date = date.replace(tzinfo=None)

        # Allow caller to pass db=None; open our own session in that case
        from db.database import SessionLocal as _SL

        own_session = db is None
        if own_session:
            db = _SL()

        try:
            metrics = crud.get_or_create_daily_metrics(db, user_id, exchange, date)

            next_day = date + timedelta(days=1)
            trades = (
                db.query(models.Trades)
                .filter(
                    models.Trades.user_id == user_id,
                    models.Trades.exchange == exchange,
                    models.Trades.status == "closed",
                    models.Trades.exit_time >= date,
                    models.Trades.exit_time < next_day,
                )
                .all()
            )

            if not trades:
                return metrics

            metrics.total_trades = len(trades)
            metrics.winning_trades = sum(1 for t in trades if t.result == 1)
            metrics.losing_trades = sum(1 for t in trades if t.result == -1)
            metrics.breakeven_trades = sum(1 for t in trades if t.result == 0)

            metrics.gross_profit = sum(t.pnl_abs for t in trades if t.pnl_abs > 0)
            metrics.gross_loss = sum(t.pnl_abs for t in trades if t.pnl_abs < 0)
            metrics.total_pnl = sum(t.pnl_abs for t in trades)
            metrics.total_fees = sum(t.total_fees for t in trades if t.total_fees)
            metrics.net_pnl = metrics.total_pnl

            metrics.win_rate = cls.calculate_win_rate(trades)
            metrics.profit_factor = cls.calculate_profit_factor(trades)

            avg_pnl = cls.calculate_average_trades(trades)
            metrics.avg_win = avg_pnl["avg_win"]
            metrics.avg_loss = avg_pnl["avg_loss"]
            metrics.avg_trade = avg_pnl["avg_trade"]

            streaks = cls.calculate_streaks(trades)
            metrics.max_consecutive_wins = streaks["max_consecutive_wins"]
            metrics.max_consecutive_losses = streaks["max_consecutive_losses"]
            metrics.current_streak = streaks["current_streak"]

            db.commit()
            db.refresh(metrics)
            return metrics
        except Exception as e:
            logger.error(f"Error updating daily metrics: {e}")
            db.rollback()
            return None
        finally:
            if own_session:
                db.close()

    @classmethod
    def update_strategy_performance(
        cls, db: Session, user_id: int, strategy: str, exchange: str
    ):
        """Update aggregated performance for a strategy"""
        from db.database import SessionLocal as _SL

        own_session = db is None
        if own_session:
            db = _SL()

        try:
            performance = crud.get_or_create_strategy_performance(
                db, user_id, strategy, exchange
            )

            trades = crud.get_trades_by_strategy(db, user_id, strategy, limit=1000)
            trades = [t for t in trades if t.exchange == exchange]
            closed_trades = [t for t in trades if t.status == "closed"]

            if not closed_trades:
                return performance

            performance.total_trades = len(closed_trades)
            performance.winning_trades = sum(1 for t in closed_trades if t.result == 1)
            performance.losing_trades = sum(1 for t in closed_trades if t.result == -1)

            performance.total_pnl = sum(t.pnl_abs for t in closed_trades)
            performance.win_rate = cls.calculate_win_rate(closed_trades)
            performance.profit_factor = cls.calculate_profit_factor(closed_trades)

            avg_pnl = cls.calculate_average_trades(closed_trades)
            performance.avg_win = avg_pnl["avg_win"]
            performance.avg_loss = avg_pnl["avg_loss"]

            streaks = cls.calculate_streaks(closed_trades)
            performance.max_consecutive_wins = streaks["max_consecutive_wins"]
            performance.max_consecutive_losses = streaks["max_consecutive_losses"]
            performance.current_streak = streaks["current_streak"]

            performance.first_trade_at = min(
                t.entry_time for t in closed_trades if t.entry_time
            )
            performance.last_trade_at = max(
                t.exit_time for t in closed_trades if t.exit_time
            )

            equity_curve = cls.generate_equity_curve(db, user_id, exchange, days=90)
            drawdown = cls.calculate_drawdown([e.model_dump() for e in equity_curve])
            performance.max_drawdown = drawdown["max_drawdown"]
            performance.max_drawdown_pct = drawdown["max_drawdown_pct"]

            crud.update_strategy_performance(db, performance)
            return performance
        except Exception as e:
            logger.error(f"Error updating strategy performance: {e}")
            db.rollback()
            return None
        finally:
            if own_session:
                db.close()

    @classmethod
    def track_drawdown(
        cls, db: Session, user_id: int, exchange: str, current_balance: float
    ):
        """
        Track drawdown periods correctly:
        - One active (unrecovered) DrawdownRecord at a time.
        - A new record is only created when a real drawdown STARTS
          (balance drops below the known peak).
        - A record is only marked recovered when balance >= peak.
        - We do NOT create a new record just because the balance hit a new high
          while already recovered; we simply update the existing record's peak.
        """
        active_drawdown = crud.get_active_drawdown(db, user_id, exchange)

        if active_drawdown:
            # Update trough / recovery on the existing active record
            crud.update_drawdown(db, active_drawdown, current_balance)
            # If recovered, the record is now closed (recovered=True).
            # The next time balance drops we'll create a fresh one below.
        else:
            # No active drawdown — check whether one is starting now.
            last_balance = crud.get_latest_balance(db, user_id, exchange)
            if last_balance and current_balance < last_balance.amount:
                # Balance dropped below previous record → new drawdown starts
                crud.create_drawdown_record(db, user_id, exchange, last_balance.amount)
            # If current_balance >= last_balance (new peak or flat), nothing to do.

    @classmethod
    def calculate_position_heatmap(
        cls, db: Session, user_id: int, exchange: str, hours: int = 24
    ) -> List[Dict]:
        """Calculate position heatmap data"""
        snapshots = crud.get_position_snapshots(db, user_id, exchange, hours)

        # Group by pair
        pair_data = defaultdict(
            lambda: {"timestamps": [], "sizes": [], "pnls": [], "margins": []}
        )

        for snapshot in snapshots:
            pair = snapshot.pair
            pair_data[pair]["timestamps"].append(snapshot.timestamp)
            pair_data[pair]["sizes"].append(snapshot.position_size)
            pair_data[pair]["pnls"].append(snapshot.unrealized_pnl)
            pair_data[pair]["margins"].append(snapshot.margin_used)

        # Calculate heatmap metrics
        heatmap = []
        for pair, data in pair_data.items():
            if not data["sizes"]:
                continue

            avg_size = sum(abs(s) for s in data["sizes"]) / len(data["sizes"])
            total_pnl = sum(data["pnls"])
            avg_margin = sum(data["margins"]) / len(data["margins"])
            max_size = max(abs(s) for s in data["sizes"])
            min_size = min(abs(s) for s in data["sizes"])

            heatmap.append(
                {
                    "pair": pair,
                    "avg_position_size": round(avg_size, 4),
                    "max_position_size": round(max_size, 4),
                    "min_position_size": round(min_size, 4),
                    "unrealized_pnl": round(total_pnl, 2),
                    "avg_margin_used": round(avg_margin, 2),
                    "data_points": len(data["sizes"]),
                    "last_updated": max(data["timestamps"])
                    if data["timestamps"]
                    else None,
                }
            )

        # Sort by absolute position size (most active first)
        heatmap.sort(key=lambda x: x["avg_position_size"], reverse=True)

        return heatmap

    @classmethod
    def calculate_returns_by_period(
        cls, db: Session, user_id: int, exchange: str
    ) -> Dict[str, Dict[str, float]]:
        """Calculate returns by daily, weekly, and monthly periods"""
        now = datetime.now(timezone.utc)

        # Daily return (last 24 hours)
        daily_trades = (
            db.query(models.Trades)
            .filter(
                models.Trades.user_id == user_id,
                models.Trades.exchange == exchange,
                models.Trades.status == "closed",
                models.Trades.exit_time >= now - timedelta(days=1),
            )
            .all()
        )
        daily_pnl = sum(t.pnl_abs for t in daily_trades)

        # Weekly return (last 7 days)
        weekly_trades = (
            db.query(models.Trades)
            .filter(
                models.Trades.user_id == user_id,
                models.Trades.exchange == exchange,
                models.Trades.status == "closed",
                models.Trades.exit_time >= now - timedelta(days=7),
            )
            .all()
        )
        weekly_pnl = sum(t.pnl_abs for t in weekly_trades)

        # Monthly return (last 30 days)
        monthly_trades = (
            db.query(models.Trades)
            .filter(
                models.Trades.user_id == user_id,
                models.Trades.exchange == exchange,
                models.Trades.status == "closed",
                models.Trades.exit_time >= now - timedelta(days=30),
            )
            .all()
        )
        monthly_pnl = sum(t.pnl_abs for t in monthly_trades)

        # Get starting balance for percentage calculation
        latest_balance = crud.get_latest_balance(db, user_id, exchange)
        balance = latest_balance.amount if latest_balance else 1000.0

        return {
            "daily": {
                "pnl": round(daily_pnl, 2),
                "trades": len(daily_trades),
                "return_pct": round((daily_pnl / balance) * 100, 2)
                if balance > 0
                else 0.0,
            },
            "weekly": {
                "pnl": round(weekly_pnl, 2),
                "trades": len(weekly_trades),
                "return_pct": round((weekly_pnl / balance) * 100, 2)
                if balance > 0
                else 0.0,
            },
            "monthly": {
                "pnl": round(monthly_pnl, 2),
                "trades": len(monthly_trades),
                "return_pct": round((monthly_pnl / balance) * 100, 2)
                if balance > 0
                else 0.0,
            },
        }


# Global calculator instance
metrics_calculator = MetricsCalculator()
