import requests
from sqlalchemy.orm import Session
from db import crud, models, schemas
from db.database import SessionLocal, engine
import importlib
from datetime import datetime

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

class ThreadTemplate():
    def __init__(self, thread_id, user_id, pair, exchange, qty, leverage, message):
        self.timestamp = datetime.now()
        self.strategy_name = ''
        self.thread_id = thread_id
        self.user_id = user_id
        self.pair = pair
        self.exchange = exchange
        self.qty = qty
        self.leverage = int(leverage)
        self.message = message
        self.client = self.api_init(user_id, exchange, pair)
   
    def api_init(self, user_id, exchange, pair):
        key = crud.get_key(db, exchange=exchange, user_id=user_id)

        if key is None:
            print("Key not found")
        
        module_name = f"exchange.{exchange}"
        class_name = f"Exchange"
        module = importlib.import_module(module_name)
        exchange_class = getattr(module, class_name)
        client = exchange_class(api_key=key.api_key, api_secret=key.api_secret, symbol=pair)
        return client

    def create_trade(self, action, entry, profit, loss):
        trade = schemas.Trades(
            user_id = self.user_id,
            exchange = self.exchange,
            pair = self.pair,
            qty = self.qty,
            leverage = self.leverage,
            action = action,
            result = 0,
            strategy = self.strategy_name,
            entry = entry,
            profit = profit,
            loss = loss
            )
        crud.create_trade(db, trade)

    def update_trade_result(self, price):
        crud.update_trade_result(db, self.user_id, self.pair, self.exchange, price)

    def update_balance(self, amount):
        crud.update_balance(db, self.user_id, self.exchange, amount)

    def heartbeat(self):
        crud.update_thread_heartbeat(db, self.thread_id)
        self.timestamp = datetime.now()

    def execute(self):
        # This will be implemented in the specific strategy classes
        self.heartbeat()
        self.timestamp = datetime.now()


