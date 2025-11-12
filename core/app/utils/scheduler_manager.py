from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
#import logging
from db.database import SessionLocal
from db import crud
import importlib
import json


class Scheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(
            executors={
                'default': ThreadPoolExecutor(1)
            },
            job_defaults={
                'max_instances': 3,
                'misfire_grace_time': 30
            }
        )

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()

            self.load_strategy()

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            print('scheduler stopped')

    def add_strategy(self, db_thread, strategy_instance, interval=60):
        interval = self._get_interval(db_thread.strategy)
    
        cron_expression = self._interval_to_cron(interval)

        job = self.scheduler.add_job(
            strategy_instance.execute,
            'cron',
            **cron_expression,
            id=f"strategy_{db_thread.id}",
            replace_existing=True
        )

        print(f"strategy {db_thread.id} every {interval} seconds")

    def _get_interval(self, strategy_name):
        try:
            with open(f"threads/{strategy_name}/config.json", "r") as f:
                config = json.load(f)
                return config.get("interval", 60)
        except:
            return 60

    def _interval_to_cron(self, interval):
        if interval >= 3600:
            hours = interval // 3600
            return {'hour': f'*/{hours}'}
        elif interval >= 60:
            minutes = interval // 60
            return {'minute': f'*/{minutes}'}
        else:
            return {'second': f'*/{interval}'}

    def stop_strategy(self, thread_id):
        try:
            job_id = f"strategy_{thread_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                print(f"strategy {thread_id} stopped")
        except Exception as e:
            print(f"{e}")

    def load_strategy(self):
        db = SessionLocal()
        try:
            db_threads = crud.get_all_threads(db)
            for db_thread in db_threads:
                if db_thread.status == 'running':
                    try:
                        self._restart(db_thread)
                    except Exception as e:
                        print(f'{e}')
        except Exception as e:
            print(f'{e}')
        finally:
            db.close()

    def _restart(self, db_thread):
        try:
            module_name = f"threads.{db_thread.strategy}.main"
            strategy_module = importlib.import_module(module_name)
            strategy_class = getattr(strategy_module, 'Strategy')

            strategy_instance = strategy_class(db_thread.id, db_thread.user_id, db_thread.pair, db_thread.exchange, db_thread.qty, db_thread.leverage, "")
            interval = 60
            self.add_strategy(db_thread, strategy_instance, interval)
        except Exception as e:
            print(f"{e}")

scheduler_manager = Scheduler() 
