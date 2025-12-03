from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, BigInteger
from sqlalchemy.orm import relationship

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

    trades = relationship("Trades", back_populates="owner")
    keys = relationship("Keys", back_populates="owner")
    threads = relationship("Threads", back_populates="owner")
    balance = relationship("Balance", back_populates="owner")


class Trades(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exchange = Column(String)
    pair = Column(String, index=True)
    qty = Column(Integer)
    leverage = Column(Integer)
    action = Column(Integer)
    result = Column(Integer)
    strategy = Column(String)
    entry = Column(Float)
    profit = Column(Float)
    loss = Column(Float)

    owner = relationship("User", back_populates="trades")


class Keys(Base):
    __tablename__ = "keys"

    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    api_key = Column(String)
    api_secret = Column(String)

    owner = relationship("User", back_populates="keys")


class Threads(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    pair = Column(String, index=True)
    qty = Column(Integer)
    exchange = Column(String)
    leverage = Column(Integer)
    strategy = Column(String)
    message = Column(String)
    status = Column(String)
    last_heartbeat = Column(Integer)

    owner = relationship("User", back_populates="threads")

class Balance(Base):
    __tablename__ = "balance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exchange = Column(String)
    amount = Column(Float)
    timestamp = Column(BigInteger)

    owner = relationship("User", back_populates="balance")
