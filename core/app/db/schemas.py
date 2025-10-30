from pydantic import BaseModel

class KeyBase(BaseModel):
    exchange: str
    api_key: str 
    api_secret: str

    class Config:
        orm_mode = True

class KeyCreate(KeyBase):
    pass


class TradeBase(BaseModel):
    user_id: int

class Trade(TradeBase):
    id: int 
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
        orm_mode = True



class UserBase(BaseModel):
    name: str
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    password: str
    trades: list[Trade] = []

    class Config:
        orm_mode = True

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
        orm_mode = True

