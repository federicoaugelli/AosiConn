from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime, timezone, timedelta

# user CRUD
def get_user(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_all_users(db: Session):
    return db.query(models.User).all()

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
    return db.query(models.Trades).filter(models.Trades.user_id == user_id).all()

def get_trade_by_pair(db: Session, user_id: int, pair: str):
    return db.query(models.Trades).filter(models.Trades.user_id == user_id, models.Trades.pair == pair).all()

def create_trade(db: Session, trade: schemas.Trades):
    add_trade = models.Trades(
        user_id = trade.user_id, 
        exchange = trade.exchange,
        pair = trade.pair, 
        qty = trade.qty, 
        leverage = trade.leverage, 
        action = trade.action, 
        result = trade.result, 
        strategy = trade.strategy, 
        entry = trade.entry, 
        profit = trade.profit, 
        loss = trade.loss
    )
    db.add(add_trade)
    db.commit()
    db.refresh(add_trade)
    return add_trade

def update_trade_result(db: Session, user_id: int, pair: str, exchange: str, price: int):
    trade = db.query(models.Trades).filter(models.Trades.user_id == user_id, models.Trades.pair == pair, models.Trades.exchange == exchange).order_by(models.Trades.id.desc()).first()

    if trade.action > 0:
        if price > trade.entry:
            trade.result = 1
        else:
            trade.result = -1
    else:
        if price < trade.entry:
            trade.result = 1
        else:
            trade.result = -1

    db.commit()
    db.refresh(trade)
    return trade

# thread CRUD
def create_thread(db: Session, user_id: int, pair: str, exchange: str, qty: int, leverage: int, message: str, strategy: str):
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
def update_balance(db: Session, user_id: int, exchange: str, amount: float):
    today = datetime.now(timezone.utc).date()
    
    last_balance = db.query(models.Balance).filter(
        models.Balance.user_id == user_id, 
        models.Balance.exchange == exchange
    ).order_by(models.Balance.timestamp.desc()).first()

    if last_balance:
        last_balance_date = datetime.fromtimestamp(
            last_balance.timestamp, tz=timezone.utc
        ).date()

        if last_balance_date == today:
            last_balance.amount = amount
            last_balance.timestamp = int(datetime.now(timezone.utc).timestamp())
            db.commit()
            db.refresh(last_balance)
            return last_balance

    print(f"old balance: {last_balance}")

    new_balance = models.Balance(
        user_id=user_id,
        exchange=exchange,
        amount=amount,
        timestamp=int(datetime.now(timezone.utc).timestamp())
    )

    print(f"new balance: {new_balance.user_id}, {new_balance.exchange}, {new_balance.amount}, {new_balance.timestamp}")
    db.add(new_balance)
    db.commit
    db.refresh(new_balance)
    return new_balance

def get_balance(db: Session, user_id: int, exchange: str, days: int = 30):
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days = days)

    query = db.query(models.Balance).filter(
        models.Balance.user_id == user_id,
        models.Balance.exchange == exchange,
        models.Balance.timestamp >= int(start_date.timestamp())
    )

    bal = query.order_by(models.Balance.timestamp.desc()).all()
    return bal
    #return db.query(models.Balance).filter(models.Balance.user_id == user_id, models.Balance.exchange == exchange).all()
