"""
/portfolio routes — authenticated portfolio management.

All routes require a valid Firebase token (get_current_user dependency).
No business logic lives here: routes parse the request, call the service,
and build the HTTP response.

Route order note: literal paths (/portfolios, /dividends, /lines)
are registered before parametric paths to avoid shadowing.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models import User
from app.schemas.portfolio import (
    DividendReceived,
    PortfolioCreate,
    PortfolioLineCreate,
    PortfolioRead,
)
from app.services import portfolio_service
from app.utils.exceptions import (
    PortfolioNotFoundError,
    PositionNotFoundError,
    StockNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# ── Helper ────────────────────────────────────────────────────────────────────


def _portfolio_response(
    session: Session, portfolio_id: int, user_id: int
) -> PortfolioRead:
    """Build a PortfolioRead from a fully-valued portfolio dict."""
    data = portfolio_service.get_portfolio_with_valuation(session, portfolio_id, user_id)
    return PortfolioRead.model_validate(data)


# ── Portfolio-level routes (must come before /{...} if any) ──────────────────


@router.get("/portfolios")
def list_portfolios(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> List[dict]:
    """List all portfolios belonging to the authenticated user."""
    portfolios = portfolio_service.list_portfolios(session, user.id)
    return [{"id": p.id, "name": p.name} for p in portfolios]


@router.post("/portfolios", status_code=status.HTTP_201_CREATED)
def create_portfolio(
    body: PortfolioCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Create a new named portfolio for the authenticated user."""
    portfolio = portfolio_service.create_portfolio(session, user.id, body.name)
    return {"id": portfolio.id, "name": portfolio.name}


# ── Default portfolio routes ──────────────────────────────────────────────────


@router.get("/", response_model=PortfolioRead)
def get_portfolio(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PortfolioRead:
    """
    Return the user's default portfolio with real-time valuation.

    Auto-creates a portfolio named 'Mon portefeuille' if none exists.
    """
    portfolio = portfolio_service.get_or_create_default_portfolio(session, user.id)
    return _portfolio_response(session, portfolio.id, user.id)


@router.post("/lines", response_model=PortfolioRead)
def add_line(
    body: PortfolioLineCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PortfolioRead:
    """
    Add shares to the default portfolio, consolidating the PRU if the
    stock is already present.

    Returns the full updated portfolio valuation.
    """
    portfolio = portfolio_service.get_or_create_default_portfolio(session, user.id)
    try:
        portfolio_service.add_or_update_line(
            session, portfolio.id, user.id,
            body.symbol, body.quantity, body.price,
        )
    except StockNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    return _portfolio_response(session, portfolio.id, user.id)


@router.delete("/lines/{line_id}", response_model=PortfolioRead)
def remove_line(
    line_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PortfolioRead:
    """
    Remove a position from the default portfolio.

    Returns the full updated portfolio valuation.
    """
    portfolio = portfolio_service.get_or_create_default_portfolio(session, user.id)
    try:
        portfolio_service.remove_line(session, portfolio.id, user.id, line_id)
    except (PortfolioNotFoundError, PositionNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    return _portfolio_response(session, portfolio.id, user.id)


@router.post("/dividends", response_model=PortfolioRead)
def record_dividends(
    body: DividendReceived,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PortfolioRead:
    """
    Record dividends received for a position in the default portfolio.

    Adds (quantity × amount_per_share) to total_dividends_received for that line.
    Returns the full updated portfolio valuation.
    """
    portfolio = portfolio_service.get_or_create_default_portfolio(session, user.id)
    try:
        portfolio_service.record_dividends_received(
            session, portfolio.id, user.id,
            body.symbol, body.amount_per_share,
        )
    except StockNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except PositionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    return _portfolio_response(session, portfolio.id, user.id)
