from datetime import date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .stock import Stock


class DailyPrice(SQLModel, table=True):
    __tablename__ = "daily_prices"
    __table_args__ = (UniqueConstraint("stock_id", "trading_date"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)
    trading_date: date = Field(index=True)
    open_price: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)
    high_price: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)
    low_price: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)
    close_price: Decimal = Field(max_digits=12, decimal_places=2)
    volume: int = Field(default=0)
    variation_pct: Optional[Decimal] = Field(default=None, max_digits=6, decimal_places=2)

    stock: Optional["Stock"] = Relationship(back_populates="daily_prices")
