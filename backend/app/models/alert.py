from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


class Alert(SQLModel, table=True):
    __tablename__ = "alerts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    stock_id: int = Field(foreign_key="stocks.id")
    condition_type: str
    threshold: Decimal
    last_trigger_state: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
