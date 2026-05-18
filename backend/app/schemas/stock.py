from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class StockOut(BaseModel):
    id: int
    ticker: str
    name: str
    sector: Optional[str]
    country: str
    isin: Optional[str]


class DailyPriceOut(BaseModel):
    trading_date: date
    open_price: Optional[Decimal]
    close_price: Decimal
    volume: Optional[int]


class StockFullOut(StockOut):
    prices: list[DailyPriceOut] = []
    per: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
