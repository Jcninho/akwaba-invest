from typing import Optional

from sqlmodel import Field, SQLModel


class Stock(SQLModel, table=True):
    __tablename__ = "stocks"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(unique=True, index=True)
    name: str
    sector: Optional[str] = None
    country: str
    isin: Optional[str] = None
