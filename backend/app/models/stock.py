from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .price import DailyPrice
    from .financial import Financial
    from .dividend import Dividend


class Stock(SQLModel, table=True):
    __tablename__ = "stocks"

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(max_length=10, unique=True, index=True)
    name: str = Field(max_length=100)
    sector: str = Field(max_length=50)
    country: str = Field(max_length=50)
    shares_outstanding: Optional[int] = Field(default=None)
    float_pct: Optional[Decimal] = Field(default=None, max_digits=5, decimal_places=2)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    daily_prices: List["DailyPrice"] = Relationship(back_populates="stock")
    financials: List["Financial"] = Relationship(back_populates="stock")
    dividends: List["Dividend"] = Relationship(back_populates="stock")
