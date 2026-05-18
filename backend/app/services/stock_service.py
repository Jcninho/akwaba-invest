import logging
from typing import Optional

from sqlmodel import Session

logger = logging.getLogger(__name__)


def get_all_stocks(session: Session) -> list:
    # TODO: query stocks table, return list of Stock models
    raise NotImplementedError


def get_stock_by_ticker(ticker: str, session: Session):
    # TODO: query stocks by ticker; raise 404 if not found
    raise NotImplementedError


def get_stock_prices(ticker: str, session: Session, limit: Optional[int] = 30) -> list:
    # TODO: query daily_prices joined with stocks by ticker; order by trading_date desc
    raise NotImplementedError


def get_stock_full_detail(ticker: str, session: Session) -> dict:
    # TODO: aggregate stock + financials + dividends + price history (5 years)
    raise NotImplementedError
