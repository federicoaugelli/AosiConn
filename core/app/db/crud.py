from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime

# user CRUD
def get_user(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(name=user.name, username=user.username, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# key CRUD
def get_key(db: Session, user_id: int, exchange: str):
    return db.query(models.Keys).filter(models.Keys.user_id == user_id, models.Keys.exchange == exchange).first()


def get_keys(db: Session, user_id: int):
    return db.query(models.Keys).filter(models.Keys.user_id == user_id).all()


def modify_key(db: Session, user_id: int, exchange: str, api_key: str, api_secret: str):
    key = db.query(models.Keys).filter(models.Keys.user_id == user_id, models.Keys.exchange == exchange).first()
    key.api_key = api_key
    key.api_secret = api_secret
    db.commit()
    db.refresh(key)
    return key


def create_key(db: Session, key: schemas.KeyBase, user_id):
    db_key = models.Keys(exchange=key.exchange, user_id=user_id, api_key=key.api_key, api_secret=key.api_secret)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key


def delete_key(db: Session, user_id: int, exchange: str):
    key = db.query(models.Keys).filter(models.Keys.user_id == user_id, models.Keys.exchange == exchange).first()
    db.delete(key)
    db.commit()
    return key

# trade CRUD
def get_all_trade(db: Session, user_id: int):
    return db.query(models.Trade).filter(models.Trade.user_id == user_id).all()

def get_trade_by_pair(db: Session, user_id: int, pair: str):
    return db.query(models.Trade).filter(models.Trade.user_id == user_id, models.Trade.pair == pair).all()


def create_trade(db: Session, trade: schemas.Trade):
    add_trade = models.Trade(user_id = trade.user_id, pair = trade.pair, qty = trade.qty, leverage = trade.leverage, action = trade.action, result = trade.result, strategy = trade.strategy, entry = trade.entry, profit = trade.profit, loss = trade.loss)
    db.add(add_trade)
    db.commit()
    db.refresh(add_trade)
    return add_trade

# thread CRUD
def create_thread(db: Session, user_id: int, pair: str, qty: int, leverage: int, strategy: str):
    db_thread = models.Threads(
        user_id=user_id,
        pair=pair,
        qty=qty,
        leverage=leverage,
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


