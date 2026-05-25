"""
Pydantic schemas for alert management endpoints.

AlertCreate validates the user's intent; threshold is required for price
alerts and forbidden (or ignored) for dividend alerts.
AlertRead carries the enriched response (symbol + stock_name from the
Stock table, which is joined by the service layer).
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class AlertCreate(BaseModel):
    """Body for POST /alerts/ — create a new alert."""

    symbol: str
    alert_type: str  # 'price_above' | 'price_below' | 'dividend'
    threshold: Optional[Decimal] = None  # required for price alerts, ignored for dividend

    @field_validator("alert_type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        allowed = {"price_above", "price_below", "dividend"}
        if v not in allowed:
            raise ValueError(f"alert_type must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def threshold_required_for_price(self) -> "AlertCreate":
        if self.alert_type in ("price_above", "price_below"):
            if self.threshold is None:
                raise ValueError("threshold is required for price alerts")
            if self.threshold <= 0:
                raise ValueError("threshold must be > 0")
        return self


class AlertRead(BaseModel):
    """Full representation of one alert returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str           # from Stock (joined by service)
    stock_name: str       # from Stock (joined by service)
    alert_type: str
    threshold: Optional[Decimal] = None
    is_active: bool
    last_triggered_at: Optional[datetime] = None


class AlertToggle(BaseModel):
    """Body for PATCH /alerts/{id}/toggle — activate or deactivate."""

    is_active: bool
