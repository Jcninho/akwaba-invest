from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


class Financial(SQLModel, table=True):
    __tablename__ = "financials"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id")
    fiscal_year: int
    revenue: Optional[Decimal] = None
    net_income: Optional[Decimal] = None
    total_debt: Optional[Decimal] = None
    eps: Optional[Decimal] = None
