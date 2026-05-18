from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolios"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    name: str = Field(default="My Portfolio")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PortfolioLine(SQLModel, table=True):
    __tablename__ = "portfolio_lines"

    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolios.id")
    stock_id: int = Field(foreign_key="stocks.id")
    quantity: int
    pru: Decimal
    purchase_date: Optional[date] = None
