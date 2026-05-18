import pytest
from sqlmodel import Session

from app.services.stock_service import (
    get_all_stocks,
    get_stock_by_ticker,
    get_stock_prices,
)


def test_get_all_stocks_returns_list(session: Session) -> None:
    # TODO: insert fixture stocks, assert list is returned
    pass


def test_get_stock_by_ticker_not_found_raises(session: Session) -> None:
    # TODO: assert 404-equivalent exception raised for unknown ticker
    pass


def test_get_stock_prices_empty_when_no_data(session: Session) -> None:
    # TODO: assert empty list returned for stock with no price history
    pass
