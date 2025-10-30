from pydantic import BaseModel

class insert_strategy(BaseModel):
    strategy: str
    pair: str
    exchange: str
    qty: int
    leverage: int
    message: str | None = None

class update_strategy(BaseModel):
    thread_id: int
    pair: str | None = None
    exchange: str | None = None
    qty: int | None = None
    leverage: int | None = None
    message: str | None = None
