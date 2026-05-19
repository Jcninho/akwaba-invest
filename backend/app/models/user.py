from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .subscription import Subscription
    from .portfolio import Portfolio
    from .alert import Alert


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    firebase_uid: str = Field(max_length=128, unique=True, index=True)
    email: str = Field(max_length=255, unique=True, index=True)
    plan: str = Field(default="free", max_length=10)  # 'free' | 'premium'
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    subscriptions: List["Subscription"] = Relationship(back_populates="user")
    portfolios: List["Portfolio"] = Relationship(back_populates="user")
    alerts: List["Alert"] = Relationship(back_populates="user")
