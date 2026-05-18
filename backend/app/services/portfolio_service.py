import logging
from decimal import Decimal

from sqlmodel import Session

logger = logging.getLogger(__name__)


def get_user_portfolio(user_id: str, session: Session) -> dict:
    # TODO: return portfolio with all lines, current prices, Total Return
    raise NotImplementedError


def add_portfolio_line(
    user_id: str,
    ticker: str,
    quantity: int,
    purchase_price: Decimal,
    session: Session,
) -> dict:
    # TODO: compute consolidated PRU, persist portfolio_line, return updated portfolio
    raise NotImplementedError


def delete_portfolio_line(user_id: str, line_id: int, session: Session) -> None:
    # TODO: verify ownership, delete line, update portfolio totals
    raise NotImplementedError


def compute_consolidated_pru(
    old_qty: int,
    old_pru: Decimal,
    new_qty: int,
    purchase_price: Decimal,
) -> Decimal:
    if new_qty <= 0:
        raise ValueError("new_qty must be > 0")
    total_qty = old_qty + new_qty
    return (Decimal(old_qty) * old_pru + Decimal(new_qty) * purchase_price) / Decimal(total_qty)
