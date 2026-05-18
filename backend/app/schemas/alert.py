from decimal import Decimal

from pydantic import BaseModel


class AlertIn(BaseModel):
    ticker: str
    condition_type: str
    threshold: Decimal


class AlertOut(BaseModel):
    id: int
    ticker: str
    condition_type: str
    threshold: Decimal
    last_trigger_state: bool
