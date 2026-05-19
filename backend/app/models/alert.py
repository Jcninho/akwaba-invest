from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class Alert(SQLModel, table=True):
    __tablename__ = "alerts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)
    alert_type: str = Field(max_length=20)  # 'price_above' | 'price_below' | 'dividend'
    threshold: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)
    is_active: bool = Field(default=True)
    last_trigger_state: bool = Field(default=False)
    last_triggered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="alerts")
