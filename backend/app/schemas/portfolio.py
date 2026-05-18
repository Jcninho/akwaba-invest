from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PortfolioLineIn(BaseModel):
    ticker: str
    quantity: int
    purchase_price: Decimal
    purchase_date: Optional[date] = None


class PortfolioLineOut(BaseModel):
    id: int
    ticker: str
    quantity: int
    pru: Decimal
    current_price: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]


class PortfolioOut(BaseModel):
    id: int
    name: str
    lines: list[PortfolioLineOut] = []
    total_value: Optional[Decimal]
    total_return: Optional[Decimal]
