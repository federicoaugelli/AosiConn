import asyncio
import importlib
import logging
from contextlib import contextmanager
from datetime import datetime

from db import crud, models, schemas
from db.database import SessionLocal, engine
from utils.websocket_manager import manager
from utils.metrics_service import metrics_calculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

# --- Event loop reference for cross-thread WebSocket broadcasts ---
# Set by main.py during startup so background threads can schedule
# coroutines back onto the FastAPI event loop.
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called once from the FastAPI lifespan to register the main event loop."""
    global _main_loop
    _main_loop = loop


def _broadcast(coro):
    """
    Schedule a coroutine on the main event loop from any thread.
    Silently drops the broadcast if the loop is not available.
    """
    if _main_loop is not None and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, _main_loop)


@contextmanager
def get_db_session():
    """
    Thread-safe per-call DB session.
    Each DB operation opens its own session and closes it when done,
    preventing shared-session corruption across threads.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class ThreadTemplate:
    def __init__(self, thread_id, user_id, pair, exchange, qty, leverage, message):
        self.timestamp = datetime.now()
        self.strategy_name = ""
        self.thread_id = thread_id
        self.user_id = user_id
        self.pair = pair
        self.exchange = exchange
        self.qty = float(qty)
        self.leverage = int(leverage)
        self.message = message
        self.client = self._api_init(user_id, exchange, pair)
        # Restore any existing open trade so we don't create duplicates after restart
        self.current_trade_id = self._restore_open_trade_id()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _api_init(self, user_id, exchange, pair):
        """Dynamically load exchange client from db credentials."""
        with get_db_session() as db:
            key = crud.get_key(db, exchange=exchange, user_id=user_id)

        if key is None:
            logger.error(f"API key not found for user {user_id} on {exchange}")
            return None

        try:
            module = importlib.import_module(f"exchange.{exchange}")
            exchange_class = getattr(module, "Exchange")
            client = exchange_class(
                api_key=key.api_key, api_secret=key.api_secret, symbol=pair
            )
            return client
        except Exception as e:
            logger.error(f"Error initializing exchange client: {e}")
            return None

    # Keep old name callable for any subclass that overrides it
    def api_init(self, user_id, exchange, pair):
        return self._api_init(user_id, exchange, pair)

    def _restore_open_trade_id(self) -> int | None:
        """
        On startup / restart, look for an existing open trade in the DB
        for this thread so we don't open a duplicate position.
        """
        try:
            with get_db_session() as db:
                trade = (
                    db.query(models.Trades)
                    .filter(
                        models.Trades.user_id == self.user_id,
                        models.Trades.exchange == self.exchange,
                        models.Trades.pair == self.pair,
                        models.Trades.status == "open",
                    )
                    .order_by(models.Trades.id.desc())
                    .first()
                )
                if trade:
                    logger.info(
                        f"Thread {self.thread_id}: restored open trade id={trade.id}"
                    )
                    return trade.id
        except Exception as e:
            logger.error(f"Error restoring open trade id: {e}")
        return None

    # ------------------------------------------------------------------
    # Trade management
    # ------------------------------------------------------------------

    def create_trade(
        self,
        action,
        entry_price,
        qty=None,
        stop_loss=None,
        take_profit=None,
        entry_fee=0.0,
        slippage=0.0,
        metadata=None,
    ):
        """Create a new trade. Refuses if a trade is already open."""
        if self.current_trade_id is not None:
            logger.warning(
                f"Trade {self.current_trade_id} is already open — skipping create_trade"
            )
            return None

        try:
            trade_data = schemas.TradeCreate(
                exchange=self.exchange,
                pair=self.pair,
                qty=float(qty) if qty is not None else self.qty,
                leverage=self.leverage,
                action=action,
                strategy=self.strategy_name,
                entry_price=float(entry_price),
                stop_loss=float(stop_loss) if stop_loss is not None else None,
                take_profit=float(take_profit) if take_profit is not None else None,
            )

            with get_db_session() as db:
                trade = crud.create_trade_extended(
                    db, self.user_id, trade_data, entry_fee, slippage, metadata
                )
                # Detach a plain dict snapshot so we can use it after session closes
                trade_snapshot = {
                    "id": trade.id,
                    "pair": trade.pair,
                    "strategy": trade.strategy,
                    "action": trade.action,
                    "qty": trade.qty,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "entry_time": trade.entry_time.isoformat()
                    if trade.entry_time
                    else None,
                    "exit_time": trade.exit_time.isoformat()
                    if trade.exit_time
                    else None,
                    "pnl_abs": trade.pnl_abs,
                    "pnl_pct": trade.pnl_pct,
                    "status": trade.status,
                    "result": trade.result,
                }
                trade_id = trade.id

            self.current_trade_id = trade_id
            _broadcast(self._broadcast_trade_update(trade_snapshot))
            logger.info(
                f"Created trade {trade_id} for {self.pair} ({'BUY' if action == 1 else 'SELL'})"
            )
            return trade_snapshot

        except Exception as e:
            logger.error(f"Error creating trade: {e}")
            return None

    def close_trade(self, exit_price, exit_fee=0.0):
        """Close the current open trade."""
        if not self.current_trade_id:
            logger.warning("No open trade to close")
            return None

        try:
            close_data = schemas.TradeClose(
                exit_price=float(exit_price), exit_fee=exit_fee
            )

            with get_db_session() as db:
                trade = crud.close_trade(db, self.current_trade_id, close_data)

                if not trade:
                    logger.warning(
                        f"Trade {self.current_trade_id} not found or already closed"
                    )
                    self.current_trade_id = None
                    return None

                trade_snapshot = {
                    "id": trade.id,
                    "pair": trade.pair,
                    "strategy": trade.strategy,
                    "action": trade.action,
                    "qty": trade.qty,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "entry_time": trade.entry_time.isoformat()
                    if trade.entry_time
                    else None,
                    "exit_time": trade.exit_time.isoformat()
                    if trade.exit_time
                    else None,
                    "pnl_abs": trade.pnl_abs,
                    "pnl_pct": trade.pnl_pct,
                    "status": trade.status,
                    "result": trade.result,
                }
                trade_id = trade.id
                pnl = trade.pnl_abs

            # Metrics updates — each uses its own session internally
            metrics_calculator.update_daily_metrics(
                None,  # db passed as None; method will open its own session
                self.user_id,
                self.exchange,
                datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            )
            metrics_calculator.update_strategy_performance(
                None, self.user_id, self.strategy_name, self.exchange
            )

            with get_db_session() as db:
                latest_balance = crud.get_latest_balance(
                    db, self.user_id, self.exchange
                )
                if latest_balance:
                    metrics_calculator.track_drawdown(
                        db, self.user_id, self.exchange, latest_balance.amount
                    )

            self.current_trade_id = None
            _broadcast(self._broadcast_trade_update(trade_snapshot))
            logger.info(f"Closed trade {trade_id} with P&L: ${pnl:.2f}")
            return trade_snapshot

        except Exception as e:
            logger.error(f"Error closing trade: {e}")
            return None

    def update_trade_result(self, price):
        """
        Legacy helper — marks the most recent open trade as win/loss
        based on current price vs entry. Uses entry_price (correct column).
        """
        try:
            with get_db_session() as db:
                crud.update_trade_result(
                    db, self.user_id, self.pair, self.exchange, price
                )
        except Exception as e:
            logger.error(f"Error updating trade result: {e}")

    # ------------------------------------------------------------------
    # Balance
    # ------------------------------------------------------------------

    def update_balance(
        self, amount, available=None, used_margin=None, unrealized_pnl=None
    ):
        """Update balance record in DB (avoids extra exchange API call)."""
        try:
            with get_db_session() as db:
                balance = crud.update_balance(
                    db,
                    self.user_id,
                    self.exchange,
                    amount,
                    available,
                    used_margin,
                    unrealized_pnl,
                )
                # Build snapshot before session closes
                balance_snapshot = {
                    "exchange": balance.exchange,
                    "amount": balance.amount,
                    "available": balance.available,
                    "used_margin": balance.used_margin,
                    "unrealized_pnl": balance.unrealized_pnl,
                    "timestamp": balance.timestamp,
                }
                balance_amount = balance.amount

            # Track drawdown in its own session
            with get_db_session() as db:
                metrics_calculator.track_drawdown(
                    db, self.user_id, self.exchange, balance_amount
                )

            _broadcast(self._broadcast_balance_update(balance_snapshot))
            return balance_snapshot

        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            return None

    # ------------------------------------------------------------------
    # Position snapshot
    # ------------------------------------------------------------------

    def record_position_snapshot(
        self,
        position_size,
        entry_price,
        mark_price,
        unrealized_pnl,
        margin_used,
        leverage,
        position_value,
        liquidation_price=None,
        margin_ratio=None,
    ):
        """Record a position snapshot for heatmap and tracking."""
        try:
            with get_db_session() as db:
                snapshot = crud.create_position_snapshot(
                    db,
                    self.user_id,
                    self.exchange,
                    self.pair,
                    position_size,
                    entry_price,
                    mark_price,
                    unrealized_pnl,
                    margin_used,
                    leverage,
                    position_value,
                    liquidation_price,
                    margin_ratio,
                )
                snapshot_dict = {
                    "pair": snapshot.pair,
                    "position_size": snapshot.position_size,
                    "entry_price": snapshot.entry_price,
                    "mark_price": snapshot.mark_price,
                    "unrealized_pnl": snapshot.unrealized_pnl,
                    "margin_used": snapshot.margin_used,
                    "leverage": snapshot.leverage,
                    "timestamp": snapshot.timestamp.isoformat()
                    if snapshot.timestamp
                    else None,
                }

            _broadcast(self._broadcast_position_update(snapshot_dict))
            return snapshot_dict

        except Exception as e:
            logger.error(f"Error recording position snapshot: {e}")
            return None

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def heartbeat(self):
        """Update thread heartbeat timestamp."""
        try:
            with get_db_session() as db:
                crud.update_thread_heartbeat(db, self.thread_id)
            self.timestamp = datetime.now()
        except Exception as e:
            logger.error(f"Error updating heartbeat: {e}")

    # ------------------------------------------------------------------
    # Execute (to be overridden by subclasses)
    # ------------------------------------------------------------------

    def execute(self):
        """Execute strategy logic — override in subclass."""
        self.heartbeat()
        self.timestamp = datetime.now()

    # ------------------------------------------------------------------
    # WebSocket broadcast helpers (async, run on main loop via _broadcast)
    # ------------------------------------------------------------------

    async def _broadcast_trade_update(self, trade_data: dict):
        try:
            if manager.is_user_connected(self.user_id):
                await manager.send_trade_update(self.user_id, trade_data)
        except Exception as e:
            logger.error(f"Error broadcasting trade update: {e}")

    async def _broadcast_position_update(self, snapshot_data: dict):
        try:
            if manager.is_user_connected(self.user_id):
                await manager.send_position_update(self.user_id, snapshot_data)
        except Exception as e:
            logger.error(f"Error broadcasting position update: {e}")

    async def _broadcast_balance_update(self, balance_data: dict):
        try:
            if manager.is_user_connected(self.user_id):
                await manager.send_balance_update(self.user_id, balance_data)
        except Exception as e:
            logger.error(f"Error broadcasting balance update: {e}")
