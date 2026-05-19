from typing import Optional, TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .stock import Stock


class Financial(SQLModel, table=True):
    __tablename__ = "financials"
    __table_args__ = (UniqueConstraint("stock_id", "fiscal_year"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)
    fiscal_year: int  # SMALLINT
    revenue: Optional[int] = None       # BIGINT FCFA
    net_income: Optional[int] = None    # BIGINT FCFA
    total_debt: Optional[int] = None
    equity: Optional[int] = None

    stock: Optional["Stock"] = Relationship(back_populates="financials")
