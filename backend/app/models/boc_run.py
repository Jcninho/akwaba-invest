from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class BocRun(SQLModel, table=True):
    __tablename__ = "boc_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_date: date = Field(unique=True, index=True)
    status: str = Field(max_length=10)  # 'success' | 'failed' | 'partial'
    stocks_parsed: int = Field(default=0)
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
