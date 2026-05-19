from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserRead(BaseModel):
    id: int
    email: str
    plan: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserMeResponse(BaseModel):
    id: int
    email: str
    plan: str
    subscription_end_date: Optional[datetime] = None

    class Config:
        from_attributes = True
