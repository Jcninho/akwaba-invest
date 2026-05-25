"""
/stocks routes — public market data API consumed by Flutter.

Route order matters: literal paths (/summary, /search, /top-movers)
must be registered BEFORE the parametric /{symbol} to avoid shadowing.

Auth rules:
  - All routes are public EXCEPT /dividends and /financials which
    require an active Premium subscription (require_premium dependency).
"""
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import require_premium
from app.schemas.stock import (
    DailyPriceRead,
    DividendRead,
    FinancialRead,
    MarketSummary,
    StockDetail,
    StockWithPrice,
)
from app.services import stock_service
from app.utils.exceptions import StockNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])


# ── Public — non-parametric routes (must come before /{symbol}) ───────────────


@router.get("/summary", response_model=MarketSummary)
def get_market_summary(
    session: Session = Depends(get_session),
) -> MarketSummary:
    """
    Market dashboard summary.

    Returns total stock count, up/down/unchanged breakdown,
    and the top 5 gainers and losers for the latest trading date.
    """
    data = stock_service.get_market_summary(session)
    return MarketSummary(**data)


@router.get("/search", response_model=List[StockWithPrice])
def search_stocks(
    q: str = Query(
        ...,
        min_length=2,
        description="Symbol or name to search (min 2 characters)",
    ),
    session: Session = Depends(get_session),
) -> List[StockWithPrice]:
    """
    Search stocks by symbol or name (case-insensitive, partial match).

    Returns at most 10 results with the latest price merged in.
    Query param `q` must be at least 2 characters.
    """
    results = stock_service.search_stocks(session, q)
    return [StockWithPrice(**r) for r in results]


@router.get("/top-movers")
def get_top_movers(
    date: Optional[date] = Query(  # noqa: A002 — shadows built-in intentionally
        None,
        description="Trading date (default: latest available)",
    ),
    session: Session = Depends(get_session),
) -> dict:
    """
    Top 5 gainers and top 5 losers for a given trading date.

    Stocks with no variation_pct (no-trade sessions) are excluded.
    """
    data = stock_service.get_top_movers(session, n=5, trading_date=date)
    return {
        "gainers": [StockWithPrice(**g) for g in data["gainers"]],
        "losers": [StockWithPrice(**l) for l in data["losers"]],
        "trading_date": data["trading_date"],
    }


@router.get("/", response_model=List[StockWithPrice])
def list_stocks(
    sector: Optional[str] = Query(None, description="Filter by sector name"),
    session: Session = Depends(get_session),
) -> List[StockWithPrice]:
    """
    List all active stocks with their latest price.

    Optional `sector` query param filters by exact sector name.
    """
    if sector:
        results = stock_service.get_stocks_by_sector(session, sector)
    else:
        results = stock_service.get_all_stocks_with_latest_price(session)
    return [StockWithPrice(**r) for r in results]


# ── Public — parametric single-stock routes ───────────────────────────────────


@router.get("/{symbol}", response_model=StockDetail)
def get_stock_detail(
    symbol: str,
    session: Session = Depends(get_session),
) -> StockDetail:
    """
    Full stock detail (fiche action) — public, basic info only.

    Returns stock metadata, latest price, and latest dividend.
    Premium fields (financials history) are served by /{symbol}/financials.
    """
    try:
        data = stock_service.get_stock_detail(session, symbol.upper())
    except StockNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    return StockDetail(**data)


@router.get("/{symbol}/prices", response_model=List[DailyPriceRead])
def get_stock_prices(
    symbol: str,
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Number of calendar days of history (1–365, default 30)",
    ),
    session: Session = Depends(get_session),
) -> List[DailyPriceRead]:
    """
    Price history for a stock — public.

    Returns daily OHLCV rows ordered newest-first. The window is measured
    backward from the most recent available trading date (not today) so
    results are stable regardless of when the request is made.
    """
    try:
        prices = stock_service.get_price_history(session, symbol.upper(), days)
    except StockNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    return [DailyPriceRead.model_validate(p) for p in prices]


# ── Premium — parametric routes ───────────────────────────────────────────────


@router.get("/{symbol}/dividends", response_model=List[DividendRead])
def get_stock_dividends(
    symbol: str,
    session: Session = Depends(get_session),
    _user=Depends(require_premium),
) -> List[DividendRead]:
    """
    Dividend history — requires Premium subscription.

    Returns all confirmed dividend rows ordered by fiscal year descending.
    """
    try:
        dividends = stock_service.get_dividend_history(session, symbol.upper())
    except StockNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    return [DividendRead.model_validate(d) for d in dividends]


@router.get("/{symbol}/financials", response_model=List[FinancialRead])
def get_stock_financials(
    symbol: str,
    session: Session = Depends(get_session),
    _user=Depends(require_premium),
) -> List[FinancialRead]:
    """
    Financial history (CA, résultat net, dette, capitaux propres) — requires Premium.

    Returns all financial rows ordered by fiscal year descending.
    """
    try:
        financials = stock_service.get_financial_history(session, symbol.upper())
    except StockNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    return [FinancialRead.model_validate(f) for f in financials]
