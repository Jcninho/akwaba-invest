from datetime import date
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


class DailyPrice(SQLModel, table=True):
    __tablename__ = "daily_prices"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id")
    trading_date: date
    open_price: Optional[Decimal] = None
    close_price: Decimal
    volume: Optional[int] = None
