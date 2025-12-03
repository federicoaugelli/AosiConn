from pydantic import BaseModel

# API key model
class KeyBase(BaseModel):
    exchange: str
    api_key: str 
    api_secret: str

    class Config:
        from_attributes = True

class KeyCreate(KeyBase):
    pass


class Trades(BaseModel):
    user_id: int
    exchange: str
    pair: str
    qty: float
    leverage: int
    action: int
    result: int
    strategy: str
    entry: float
    profit: float
    loss: float

    class Config:
        from_attributes = True


# User Data model
class UserBase(BaseModel):
    name: str
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    password: str
    trades: list[Trades] = []

    class Config:
        from_attributes = True


# Thread strategies model
class Thread(BaseModel):
    id: int
    user_id: int
    pair: str
    qty: int
    leverage: int
    strategy: str
    status: str
    last_heartbeat: int

    class Config:
        from_attributes = True


class Balance(BaseModel):
    id: int
    user_id: int
    exchange: str
    amount: float
    timestamp: int

    class Config:
        from_attributes: True
