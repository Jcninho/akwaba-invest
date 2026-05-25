"""
Pydantic schemas for portfolio management endpoints.

Write schemas (Create/Update) validate user input.
Read schemas (Read) carry computed fields (current_value, unrealized_gain, etc.)
that the service layer calculates from live market prices.
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class PortfolioLineCreate(BaseModel):
    """Body for POST /portfolio/lines — add or consolidate a position."""

    symbol: str
    quantity: Decimal  # shares to add, must be > 0
    price: Decimal  # purchase price per share, must be > 0

    @field_validator("quantity", "price")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("must be greater than 0")
        return v


class PortfolioLineUpdate(BaseModel):
    """Body for manual PRU/quantity override (optional, not yet routed)."""

    quantity: Optional[Decimal] = None   # new total quantity
    avg_price: Optional[Decimal] = None  # manual PRU override


class PortfolioLineRead(BaseModel):
    """Full representation of one portfolio line, with live valuation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    stock_name: str
    sector: str
    quantity: Decimal
    avg_price: Decimal                       # PRU consolidé
    current_price: Optional[Decimal] = None  # latest close price
    current_value: Optional[Decimal] = None  # quantity × current_price
    cost_basis: Decimal                      # quantity × avg_price
    unrealized_gain: Optional[Decimal] = None         # current_value − cost_basis
    unrealized_gain_pct: Optional[Decimal] = None
    total_dividends_received: Decimal
    total_return: Optional[Decimal] = None   # unrealized_gain + dividends
    trading_date: Optional[date] = None      # date of current_price


class PortfolioRead(BaseModel):
    """Full portfolio with all lines and aggregate valuation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    lines: List[PortfolioLineRead]
    total_value: Optional[Decimal] = None   # sum(quantity × current_price)
    total_cost: Decimal                     # sum(quantity × avg_price)
    total_gain: Optional[Decimal] = None    # total_value − total_cost
    total_gain_pct: Optional[Decimal] = None
    total_dividends_received: Decimal
    total_return: Optional[Decimal] = None  # total_gain + dividends
    last_updated: Optional[date] = None     # date of the price data used


class PortfolioCreate(BaseModel):
    """Body for POST /portfolio/portfolios — create a named portfolio."""

    name: str = "Mon portefeuille"


class DividendReceived(BaseModel):
    """Body for POST /portfolio/dividends — record dividends for a position."""

    symbol: str
    amount_per_share: Decimal  # net dividend per share received

    @field_validator("amount_per_share")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("must be greater than 0")
        return v
