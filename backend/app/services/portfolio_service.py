"""
Portfolio service — business logic for portfolio management.

Responsibilities:
  - PRU consolidation (compute_consolidated_pru)
  - Real-time portfolio valuation (current_price, unrealized_gain, Total Return)
  - Dividend tracking per position
  - Portfolio CRUD (create, list, get-or-create default)

All monetary calculations use Decimal. Never float.
All write functions control their own transaction (commit + rollback on error).
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from sqlmodel import Session, select

from app.models import DailyPrice, Portfolio, PortfolioLine, Stock
from app.services.stock_service import get_latest_trading_date
from app.utils.exceptions import (
    PortfolioNotFoundError,
    PositionNotFoundError,
    StockNotFoundError,
)

logger = logging.getLogger(__name__)


# ── PRU calculation ───────────────────────────────────────────────────────────


def compute_consolidated_pru(
    old_qty: Union[int, Decimal],
    old_pru: Decimal,
    new_qty: Union[int, Decimal],
    purchase_price: Decimal,
) -> Decimal:
    """
    Compute the consolidated average purchase price (PRU) after buying
    additional shares.

    Formula:
        new_avg = (old_qty × old_pru + new_qty × purchase_price)
                  / (old_qty + new_qty)

    Args:
        old_qty: Existing share count (0 for first purchase).
        old_pru: Existing average purchase price (0 for first purchase).
        new_qty: Shares being added; must be > 0.
        purchase_price: Price per share for the new batch.

    Returns:
        New consolidated average purchase price as Decimal.

    Raises:
        ValueError: If new_qty ≤ 0.
    """
    if new_qty <= 0:
        raise ValueError("new_qty must be > 0")
    total_qty = Decimal(str(old_qty)) + Decimal(str(new_qty))
    return (
        Decimal(str(old_qty)) * old_pru
        + Decimal(str(new_qty)) * purchase_price
    ) / total_qty


# ── Internal helpers ──────────────────────────────────────────────────────────


def _build_line_dict(
    line: PortfolioLine,
    stock: Stock,
    current_price: Optional[Decimal],
    trading_date: Optional[date],
) -> Dict[str, Any]:
    """
    Merge a PortfolioLine + Stock ORM object + live price into a flat dict
    that maps 1-to-1 with PortfolioLineRead fields.
    """
    cost_basis = line.quantity * line.avg_price

    current_value: Optional[Decimal] = (
        line.quantity * current_price if current_price is not None else None
    )
    unrealized_gain: Optional[Decimal] = (
        (current_value - cost_basis) if current_value is not None else None
    )
    unrealized_gain_pct: Optional[Decimal] = None
    if unrealized_gain is not None and cost_basis != 0:
        unrealized_gain_pct = (unrealized_gain / cost_basis) * Decimal("100")

    total_return: Optional[Decimal] = (
        (unrealized_gain + line.total_dividends_received)
        if unrealized_gain is not None
        else None
    )

    return {
        "id": line.id,
        "symbol": stock.symbol,
        "stock_name": stock.name,
        "sector": stock.sector,
        "quantity": line.quantity,
        "avg_price": line.avg_price,
        "current_price": current_price,
        "current_value": current_value,
        "cost_basis": cost_basis,
        "unrealized_gain": unrealized_gain,
        "unrealized_gain_pct": unrealized_gain_pct,
        "total_dividends_received": line.total_dividends_received,
        "total_return": total_return,
        "trading_date": trading_date,
    }


def _get_portfolio_or_404(
    session: Session, portfolio_id: int, user_id: int
) -> Portfolio:
    """Return portfolio or raise PortfolioNotFoundError."""
    portfolio = session.exec(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id)
        .where(Portfolio.user_id == user_id)
    ).first()
    if not portfolio:
        raise PortfolioNotFoundError(portfolio_id)
    return portfolio


# ── Public service functions ──────────────────────────────────────────────────


def get_or_create_default_portfolio(
    session: Session, user_id: int
) -> Portfolio:
    """
    Return the user's first portfolio, or create one named 'Mon portefeuille'.

    Commits the new portfolio if created.
    """
    portfolio = session.exec(
        select(Portfolio).where(Portfolio.user_id == user_id)
    ).first()

    if portfolio:
        return portfolio

    portfolio = Portfolio(user_id=user_id, name="Mon portefeuille")
    session.add(portfolio)
    session.commit()
    session.refresh(portfolio)
    logger.info("Created default portfolio for user_id=%d", user_id)
    return portfolio


def get_portfolio_with_valuation(
    session: Session, portfolio_id: int, user_id: int
) -> Dict[str, Any]:
    """
    Return a fully-valued portfolio dict compatible with PortfolioRead.

    For each line:
      - Fetches the stock record
      - Fetches the latest daily price (using the global latest trading date)
      - Computes: current_value, unrealized_gain, unrealized_gain_pct, total_return

    For the portfolio:
      - total_value   = sum of current_values (None if no prices available)
      - total_cost    = sum of cost bases (all lines, always present)
      - total_gain    = total_value − total_cost  (None if no prices)
      - total_gain_pct = total_gain / total_cost × 100  (None if no prices or zero cost)
      - total_return  = total_gain + sum(dividends)  (None if no prices)

    Raises:
        PortfolioNotFoundError: if not found or doesn't belong to user.
    """
    portfolio = _get_portfolio_or_404(session, portfolio_id, user_id)

    lines_orm = session.exec(
        select(PortfolioLine).where(PortfolioLine.portfolio_id == portfolio_id)
    ).all()

    latest_date = get_latest_trading_date(session)

    lines_data: List[Dict[str, Any]] = []
    total_cost = Decimal("0")
    total_dividends = Decimal("0")
    last_updated: Optional[date] = None

    for line in lines_orm:
        stock = session.get(Stock, line.stock_id)
        if stock is None:
            # Should never happen; FK constraint guarantees it
            logger.warning("Orphaned portfolio line %d — stock_id %d missing", line.id, line.stock_id)
            continue

        current_price: Optional[Decimal] = None
        trading_date: Optional[date] = None

        if latest_date is not None:
            price_row = session.exec(
                select(DailyPrice)
                .where(DailyPrice.stock_id == line.stock_id)
                .where(DailyPrice.trading_date == latest_date)
            ).first()
            if price_row:
                current_price = price_row.close_price
                trading_date = price_row.trading_date
                if last_updated is None or trading_date > last_updated:
                    last_updated = trading_date

        line_dict = _build_line_dict(line, stock, current_price, trading_date)
        lines_data.append(line_dict)

        total_cost += line_dict["cost_basis"]
        total_dividends += line.total_dividends_received

    # Portfolio-level aggregates
    priced_lines = [l for l in lines_data if l["current_value"] is not None]
    total_value: Optional[Decimal] = (
        sum((l["current_value"] for l in priced_lines), Decimal("0"))
        if priced_lines
        else None
    )
    total_gain: Optional[Decimal] = (
        (total_value - total_cost) if total_value is not None else None
    )
    total_gain_pct: Optional[Decimal] = None
    if total_gain is not None and total_cost != 0:
        total_gain_pct = (total_gain / total_cost) * Decimal("100")

    total_return: Optional[Decimal] = (
        (total_gain + total_dividends) if total_gain is not None else None
    )

    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "lines": lines_data,
        "total_value": total_value,
        "total_cost": total_cost,
        "total_gain": total_gain,
        "total_gain_pct": total_gain_pct,
        "total_dividends_received": total_dividends,
        "total_return": total_return,
        "last_updated": last_updated,
    }


def add_or_update_line(
    session: Session,
    portfolio_id: int,
    user_id: int,
    symbol: str,
    quantity: Decimal,
    price: Decimal,
) -> PortfolioLine:
    """
    Add shares to a portfolio position, consolidating the PRU if one exists.

    If a line for the given stock already exists:
        new_avg = (existing_qty × existing_avg + qty × price) / (existing_qty + qty)
        quantity  += qty
    Otherwise a new line is created.

    Raises:
        PortfolioNotFoundError: if portfolio doesn't exist or belong to user.
        StockNotFoundError: if the symbol is unknown.
    """
    _get_portfolio_or_404(session, portfolio_id, user_id)

    stock = session.exec(
        select(Stock).where(Stock.symbol == symbol.upper())
    ).first()
    if not stock:
        raise StockNotFoundError(symbol)

    existing = session.exec(
        select(PortfolioLine)
        .where(PortfolioLine.portfolio_id == portfolio_id)
        .where(PortfolioLine.stock_id == stock.id)
    ).first()

    if existing:
        new_avg = compute_consolidated_pru(
            old_qty=existing.quantity,
            old_pru=existing.avg_price,
            new_qty=quantity,
            purchase_price=price,
        )
        existing.quantity += quantity
        existing.avg_price = new_avg
        existing.updated_at = datetime.utcnow()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        logger.info(
            "Consolidated PRU for stock %s in portfolio %d → qty=%.4f avg=%.2f",
            symbol, portfolio_id, float(existing.quantity), float(existing.avg_price),
        )
        return existing

    line = PortfolioLine(
        portfolio_id=portfolio_id,
        stock_id=stock.id,
        quantity=quantity,
        avg_price=price,
    )
    session.add(line)
    session.commit()
    session.refresh(line)
    logger.info(
        "New line: stock %s, portfolio %d, qty=%.4f @ %.2f",
        symbol, portfolio_id, float(quantity), float(price),
    )
    return line


def remove_line(
    session: Session, portfolio_id: int, user_id: int, line_id: int
) -> None:
    """
    Remove a portfolio line by id.

    Raises:
        PortfolioNotFoundError: if portfolio doesn't exist or belong to user.
        PositionNotFoundError: if the line doesn't exist in this portfolio.
    """
    _get_portfolio_or_404(session, portfolio_id, user_id)

    line = session.exec(
        select(PortfolioLine)
        .where(PortfolioLine.id == line_id)
        .where(PortfolioLine.portfolio_id == portfolio_id)
    ).first()
    if not line:
        raise PositionNotFoundError(f"line_id={line_id}")

    session.delete(line)
    session.commit()
    logger.info("Removed portfolio line %d from portfolio %d", line_id, portfolio_id)


def record_dividends_received(
    session: Session,
    portfolio_id: int,
    user_id: int,
    symbol: str,
    amount_per_share: Decimal,
) -> PortfolioLine:
    """
    Record dividends received for a stock position.

    total_dividends_received += quantity × amount_per_share

    Raises:
        PortfolioNotFoundError: if portfolio doesn't exist or belong to user.
        StockNotFoundError: if the symbol is unknown.
        PositionNotFoundError: if no position exists for this stock.
    """
    _get_portfolio_or_404(session, portfolio_id, user_id)

    stock = session.exec(
        select(Stock).where(Stock.symbol == symbol.upper())
    ).first()
    if not stock:
        raise StockNotFoundError(symbol)

    line = session.exec(
        select(PortfolioLine)
        .where(PortfolioLine.portfolio_id == portfolio_id)
        .where(PortfolioLine.stock_id == stock.id)
    ).first()
    if not line:
        raise PositionNotFoundError(symbol)

    dividends_added = line.quantity * amount_per_share
    line.total_dividends_received += dividends_added
    line.updated_at = datetime.utcnow()
    session.add(line)
    session.commit()
    session.refresh(line)
    logger.info(
        "Recorded %.2f FCFA dividends for %s in portfolio %d",
        float(dividends_added), symbol, portfolio_id,
    )
    return line


def create_portfolio(
    session: Session, user_id: int, name: str
) -> Portfolio:
    """
    Create a new named portfolio for the user.

    No limit on the number of portfolios per user.
    """
    portfolio = Portfolio(user_id=user_id, name=name)
    session.add(portfolio)
    session.commit()
    session.refresh(portfolio)
    logger.info("Created portfolio '%s' for user_id=%d", name, user_id)
    return portfolio


def list_portfolios(session: Session, user_id: int) -> List[Portfolio]:
    """Return all portfolios belonging to the user, ordered by creation date."""
    return session.exec(
        select(Portfolio)
        .where(Portfolio.user_id == user_id)
        .order_by(Portfolio.created_at)
    ).all()
