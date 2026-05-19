from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolios"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(default="Mon portefeuille", max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="portfolios")
    lines: List["PortfolioLine"] = Relationship(
        back_populates="portfolio",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class PortfolioLine(SQLModel, table=True):
    __tablename__ = "portfolio_lines"
    __table_args__ = (UniqueConstraint("portfolio_id", "stock_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolios.id", index=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)
    quantity: Decimal = Field(max_digits=10, decimal_places=4)
    avg_price: Decimal = Field(max_digits=12, decimal_places=2)  # PRU consolidé
    total_dividends_received: Decimal = Field(default=0, max_digits=12, decimal_places=2)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    portfolio: Optional["Portfolio"] = Relationship(back_populates="lines")
