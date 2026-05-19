from datetime import date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .stock import Stock


class Dividend(SQLModel, table=True):
    __tablename__ = "dividends"
    __table_args__ = (UniqueConstraint("stock_id", "fiscal_year"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)
    fiscal_year: int
    gross_amount: Decimal = Field(max_digits=10, decimal_places=2)
    net_amount: Decimal = Field(max_digits=10, decimal_places=2)
    detachment_date: Optional[date] = None
    payment_date: Optional[date] = Field(default=None, index=True)
    is_confirmed: bool = Field(default=False)

    stock: Optional["Stock"] = Relationship(back_populates="dividends")
