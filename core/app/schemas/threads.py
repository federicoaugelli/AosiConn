from pydantic import BaseModel

class insert_strategy(BaseModel):
    strategy: str
    pair: str
    exchange: str
    qty: int
    leverage: int
    message: str

class update_strategy(BaseModel):
    thread_id: int
    pair: str
    exchange: str
    qty: int
    leverage: int
    message: str
