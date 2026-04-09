from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from db.database import SessionLocal
from db import crud
import importlib
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Heartbeat staleness threshold in seconds.
# If a thread's last_heartbeat is older than this on startup, it is
# considered crashed/stale and will NOT be auto-restored.
STALE_HEARTBEAT_SECONDS = 300  # 5 minutes


class Scheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(
            executors={
                # Single thread: strategies run sequentially, no concurrent overlap.
                "default": ThreadPoolExecutor(1)
            },
            job_defaults={
                # One instance at a time — prevents a slow job from stacking.
                "max_instances": 1,
                "misfire_grace_time": 30,
            },
        )
        # Map thread_id → strategy instance so we can update live jobs (HIGH #12)
        self._instances: dict = {}

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            self.load_strategy()

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def add_strategy(self, db_thread, strategy_instance, interval=60):
        interval = self._get_interval(db_thread.strategy)
        cron_expression = self._interval_to_cron(interval)

        self.scheduler.add_job(
            strategy_instance.execute,
            "cron",
            **cron_expression,
            id=f"strategy_{db_thread.id}",
            replace_existing=True,
        )

        # Keep a reference so PUT /instance can update the live instance
        self._instances[db_thread.id] = strategy_instance

        logger.info(f"Strategy {db_thread.id} scheduled every {interval}s")

    def update_strategy_instance(self, thread_id: int, **kwargs):
        """
        Update live strategy instance attributes after a PUT /instance call.
        Supported kwargs: qty, leverage, pair, message.
        """
        instance = self._instances.get(thread_id)
        if instance is None:
            logger.warning(f"No live instance found for thread {thread_id}")
            return False

        for key, value in kwargs.items():
            if hasattr(instance, key):
                if key == "qty":
                    setattr(instance, key, float(value))
                elif key == "leverage":
                    setattr(instance, key, int(value))
                else:
                    setattr(instance, key, value)
                logger.info(f"Thread {thread_id}: updated {key} = {value}")
            else:
                logger.warning(f"Thread {thread_id}: unknown attribute {key}")

        return True

    def _get_interval(self, strategy_name):
        try:
            with open(f"threads/{strategy_name}/config.json", "r") as f:
                config = json.load(f)
                return config.get("interval", 60)
        except Exception:
            return 60

    def _interval_to_cron(self, interval):
        if interval >= 3600:
            hours = interval // 3600
            return {"hour": f"*/{hours}"}
        elif interval >= 60:
            minutes = interval // 60
            return {"minute": f"*/{minutes}"}
        else:
            return {"second": f"*/{interval}"}

    def stop_strategy(self, thread_id):
        try:
            job_id = f"strategy_{thread_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Strategy {thread_id} stopped")
            # Release the instance reference to avoid connection leaks
            instance = self._instances.pop(thread_id, None)
            if instance is not None:
                # If the exchange client has a close/cleanup method, call it
                client = getattr(instance, "client", None)
                if client is not None:
                    close_fn = getattr(client, "close", None) or getattr(
                        client, "client", None
                    )
                    if callable(close_fn):
                        try:
                            close_fn()
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Error stopping strategy {thread_id}: {e}")

    def load_strategy(self):
        """
        On startup, restore all threads marked as 'running' in the DB,
        but skip any whose heartbeat is stale (indicating a crash mid-run).
        """
        db = SessionLocal()
        try:
            db_threads = crud.get_all_threads(db)
            now_ts = int(datetime.now(timezone.utc).timestamp())

            for db_thread in db_threads:
                if db_thread.status != "running":
                    continue

                # Stale heartbeat check — skip threads that stopped reporting
                last_hb = db_thread.last_heartbeat or 0
                age = now_ts - last_hb
                if age > STALE_HEARTBEAT_SECONDS:
                    logger.warning(
                        f"Thread {db_thread.id} heartbeat is {age}s old — marking stopped"
                    )
                    try:
                        crud.update_thread_status(db, db_thread.id, "stopped")
                    except Exception as e:
                        logger.error(
                            f"Could not mark thread {db_thread.id} stopped: {e}"
                        )
                    continue

                try:
                    self._restart(db_thread)
                except Exception as e:
                    logger.error(f"Failed to restart thread {db_thread.id}: {e}")
        except Exception as e:
            logger.error(f"Error in load_strategy: {e}")
        finally:
            db.close()

    def _restart(self, db_thread):
        module_name = f"threads.{db_thread.strategy}.main"
        strategy_module = importlib.import_module(module_name)
        strategy_class = getattr(strategy_module, "Strategy")

        strategy_instance = strategy_class(
            db_thread.id,
            db_thread.user_id,
            db_thread.pair,
            db_thread.exchange,
            db_thread.qty,
            db_thread.leverage,
            db_thread.message or "",
        )
        self.add_strategy(db_thread, strategy_instance)
        logger.info(f"Thread {db_thread.id} ({db_thread.strategy}) restarted")


scheduler_manager = Scheduler()
