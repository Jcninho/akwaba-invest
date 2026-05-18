from datetime import date
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


class Dividend(SQLModel, table=True):
    __tablename__ = "dividends"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id")
    fiscal_year: int
    amount_per_share: Decimal
    detachment_date: Optional[date] = None
    payment_date: Optional[date] = None
