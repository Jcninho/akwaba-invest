from datetime import date, datetime
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    plan_type: str = Field(max_length=10)  # 'monthly' | 'annual'
    amount_fcfa: int
    start_date: date
    end_date: date
    wave_reference: Optional[str] = Field(default=None, max_length=100)
    status: str = Field(default="active", max_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="subscriptions")
