from pydantic import BaseModel


class insert_strategy(BaseModel):
    strategy: str
    pair: str
    exchange: str
    qty: float  # float to support fractional amounts (e.g. 0.001 BTC)
    leverage: int
    message: str | None = None


class update_strategy(BaseModel):
    thread_id: int
    pair: str | None = None
    exchange: str | None = None
    qty: float | None = None  # float to support fractional amounts
    leverage: int | None = None
    message: str | None = None
