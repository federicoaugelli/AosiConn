import threading, requests
from sqlalchemy.orm import Session
from db import crud, models, schemas
from db.database import SessionLocal, engine
from exchange import bitmex
from datetime import datetime

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

class common_template(threading.Thread):
    def __init__(self, thread_id, user_id, pair, exchange, qty, leverage, message):
        threading.Thread.__init__(self)
        self.kill_it = False
        self.lock = threading.Lock()
        self.timestamp = datetime.now()
        self.timedelta = 600 # seconds
        self.strategy_name = ''
        self.thread_id = thread_id
        self.user_id = user_id
        self.pair = pair
        self.exchange = exchange
        self.stop_event = threading.Event()
        self.qty = qty
        self.leverage = int(leverage)
        self.last_action = 0
        self.message = message
        self.api_key = ''
        self.api_secret = ''
   
    #API CALLS
    def api_init(self):
        key = crud.get_key(db, exchange=self.exchange, user_id=self.user_id)

        if key is None:
            print("Key not found")
            self.stop()
            self.kill_it = True
        else:
            self.api_key = key.api_key
            self.api_secret = key.api_secret

    # decorator to set _exchange and return the function
    def prepare(self, func):
        def wrapper():
            _exchange = globals().get(self.exchange)
            return func(_exchange, *args, **kwargs)
        return wrapper

    def balance(self, currency):
        _exchange = globals().get(self.exchange)
        balance = _exchange.get_balance(self.api_key, self.api_secret, currency) 
        return balance['walletBalance']

    def quote(self, size, count):
        _exchange = globals().get(self.exchange)
        res = _exchange.get_data(size, self.pair, count)
        return res

    def ask_price(self):
        _exchange = globals().get(self.exchange)
        res = _exchange.ask_price(self.pair)
        return res

    def tick_size(self):
        _exchange = globals().get(self.exchange)
        res = _exchange.tick_size(self.pair)
        return res

    def multiplier(self):
        _exchange = globals().get(self.exchange)
        res = _exchange.multiplier(self.pair)
        return res

    def buy(self):
        _exchange = globals().get(self.exchange)
        pos = _exchange.buy(self.api_key, self.api_secret, self.pair, self.qty)
        return pos

    def sell(self):
        _exchange = globals().get(self.exchange)
        pos = _exchange.buy(self.api_key, self.api_secret, self.pair, self.qty)
        return pos

    def take_profit(self, qty, signal):
        _exchange = globals().get(self.exchange)
        res = _exchange.set_take_profit(self.api_key, self.api_secret, self.pair, qty, signal)
        return res

    def stop_loss(self, qty, signal):
        _exchange = globals().get(self.exchange)
        res = _exchange.set_stop_loss(self.api_key, self.api_secret, self.pair, qty, signal)
        return res

    def is_exit(self):
        _exchange = globals().get(self.exchange)
        res = _exchange.isExit(self.api_key, self.api_secret, self.pair)
        return res

    def cancel(self):
        _exchange = globals().get(self.exchange)
        res = _exchange.cancel_all(self.api_key, self.api_secret, self.pair)
        return res

    def create_trade(self, result, entry, profit, loss):
        trade = schemas.Trade(
            pair = self.pair,
            qty = self.qty,
            leverage = self.leverage,
            action = self.last_action,
            result = result,
            strategy = self.strategy_name,
            entry = entry,
            profit = profit,
            loss = loss
            )
        crud.create_trade(db, trade)

    def update_leverage(self):
        _exchange = globals().get(self.exchange)
        res = _exchange.leverage(self.api_key, self.api_secret, self.pair, self.leverage)
        return res
    
    def update(self, pair, exchange, qty, leverage, message):
        self.pair = pair
        self.exchange = exchange
        self.qty = qty
        self.leverage = leverage
        self.message = message

    def wait(self, seconds):
        self.stop_event.wait(seconds)
        self.timestamp = datetime.now()

    def stop(self):
        print("thread stopping...")
        self.stop_event.set()

    def heartbeat(self):
        crud.update_thread_heartbeat(db, self.thread_id)

    def run(self):
        # This will be implemented in the specific strategy classes
        while not self.stop_event.is_set():
            self.heartbeat()
            self.stop_event.wait(60) # send heartbeat every 60 seconds


