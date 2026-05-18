import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/")
async def list_stocks(session: Session = Depends(get_session)):
    # TODO: return paginated list of all BRVM stocks
    raise NotImplementedError


@router.get("/{ticker}")
async def get_stock(ticker: str, session: Session = Depends(get_session)):
    # TODO: return stock detail (basic fields, free tier)
    raise NotImplementedError


@router.get("/{ticker}/prices")
async def get_stock_prices(ticker: str, session: Session = Depends(get_session)):
    # TODO: return daily price history for the stock
    raise NotImplementedError


@router.get("/{ticker}/full")
async def get_stock_full(ticker: str, session: Session = Depends(get_session)):
    # TODO: premium — return full fiche (PER, 5-year history, financials, dividends)
    raise NotImplementedError
