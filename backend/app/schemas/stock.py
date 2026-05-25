"""
Pydantic response schemas for stock-related endpoints.

Each schema maps to a specific API response shape. ORM compatibility
is enabled via model_config so FastAPI can serialize SQLModel objects directly.
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DailyPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trading_date: date
    open_price: Optional[Decimal] = None
    close_price: Decimal
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    volume: int
    variation_pct: Optional[Decimal] = None


class DividendRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fiscal_year: int
    gross_amount: Decimal
    net_amount: Decimal
    detachment_date: Optional[date] = None
    payment_date: Optional[date] = None
    is_confirmed: bool


class FinancialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fiscal_year: int
    revenue: Optional[int] = None
    net_income: Optional[int] = None
    total_debt: Optional[int] = None
    equity: Optional[int] = None


class StockBasic(BaseModel):
    """Used in list endpoints — minimal data."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str
    name: str
    sector: str
    country: str


class StockWithPrice(BaseModel):
    """Used in market dashboard — stock + latest price merged."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str
    name: str
    sector: str
    close_price: Optional[Decimal] = None
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    volume: Optional[int] = None
    variation_pct: Optional[Decimal] = None
    trading_date: Optional[date] = None


class StockDetail(BaseModel):
    """Used in fiche action — full stock details."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str
    name: str
    sector: str
    country: str
    latest_price: Optional[DailyPriceRead] = None
    latest_dividend: Optional[DividendRead] = None


class MarketSummary(BaseModel):
    """Dashboard summary — counts and top movers."""

    model_config = ConfigDict(from_attributes=True)

    trading_date: Optional[date] = None
    total_stocks: int
    stocks_up: int
    stocks_down: int
    stocks_unchanged: int
    top_gainers: List[StockWithPrice]
    top_losers: List[StockWithPrice]


class IndexRead(BaseModel):
    """BRVM composite index snapshot."""

    name: str
    value: Optional[float] = None
    variation_pct: Optional[float] = None
