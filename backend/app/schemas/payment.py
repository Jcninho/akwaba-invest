from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubscribeIn(BaseModel):
    plan: str


class SubscribeOut(BaseModel):
    payment_url: str
    reference: str


class SubscriptionStatusOut(BaseModel):
    plan: str
    status: Optional[str]
    end_date: Optional[datetime]
