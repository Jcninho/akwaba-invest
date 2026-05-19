"""
Stock service — orchestrates BOC parsing and PostgreSQL persistence.

Core responsibility: take a parsed stock dict from boc_parser and
write it into stocks, daily_prices, and dividends tables atomically.
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.models import BocRun, DailyPrice, Dividend, Stock
from app.services.boc_run_service import (
    is_boc_run_completed,
    mark_boc_run_failed,
    mark_boc_run_success,
    start_boc_run,
)
from app.utils.boc_parser import parse_stocks_from_pdf
from app.utils.exceptions import BocParseError, NoDataError

logger = logging.getLogger(__name__)


# ── Stocks upsert ─────────────────────────────────────────────────────────────

def upsert_stock(session: Session, data: Dict[str, Any]) -> Stock:
    """
    Create or update a Stock row by symbol.

    Updates: name, sector (sector_name as country fallback), updated_at.
    Does NOT commit — caller controls the transaction.
    """
    symbol = data["symbol"]
    existing = session.exec(
        select(Stock).where(Stock.symbol == symbol)
    ).first()

    sector_name = data.get("sector_name") or data.get("sector") or ""

    if existing:
        existing.name = data["name"]
        existing.sector = sector_name
        existing.updated_at = datetime.utcnow()
        session.add(existing)
        return existing

    stock = Stock(
        symbol=symbol,
        name=data["name"],
        sector=sector_name,
        country="UEMOA",  # default — refined later via manual data import
        is_active=True,
    )
    session.add(stock)
    session.flush()  # get stock.id before returning
    return stock


# ── Daily prices upsert ───────────────────────────────────────────────────────

def upsert_daily_price(
    session: Session,
    stock_id: int,
    data: Dict[str, Any],
    trading_date: date,
) -> DailyPrice:
    """
    Create or update the daily_price row for (stock_id, trading_date).

    Idempotent via UNIQUE(stock_id, trading_date) constraint.
    Does NOT commit — caller controls the transaction.
    """
    existing = session.exec(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock_id)
        .where(DailyPrice.trading_date == trading_date)
    ).first()

    close_price = Decimal(str(data["price"]))
    open_price = (
        Decimal(str(data["open"])) if data.get("open") is not None else None
    )
    volume = int(data["volume"]) if data.get("volume") is not None else 0
    variation_pct = (
        Decimal(str(data["change_pct"])) if data.get("change_pct") is not None else None
    )

    if existing:
        existing.open_price = open_price
        existing.close_price = close_price
        existing.volume = volume
        existing.variation_pct = variation_pct
        session.add(existing)
        return existing

    price_row = DailyPrice(
        stock_id=stock_id,
        trading_date=trading_date,
        open_price=open_price,
        close_price=close_price,
        volume=volume,
        variation_pct=variation_pct,
    )
    session.add(price_row)
    return price_row


# ── Dividends upsert ──────────────────────────────────────────────────────────

def _derive_fiscal_year(dividend_date_iso: Optional[str]) -> Optional[int]:
    """Extract fiscal year from an ISO date string YYYY-MM-DD."""
    if not dividend_date_iso:
        return None
    try:
        return int(dividend_date_iso.split("-")[0])
    except (ValueError, IndexError):
        return None


def upsert_dividend(
    session: Session,
    stock_id: int,
    data: Dict[str, Any],
) -> Optional[Dividend]:
    """
    Create or update a Dividend row if the parsed data contains a dividend.

    Returns None if no dividend info is present.
    Does NOT commit — caller controls the transaction.

    The BOC publishes the "last paid dividend" — we derive fiscal_year from
    the dividend payment date. Net amount comes directly from the BOC; gross
    is approximated (real gross is in the company's annual report).
    """
    net_amount_raw = data.get("dividend")
    if net_amount_raw is None or net_amount_raw <= 0:
        return None

    fiscal_year = _derive_fiscal_year(data.get("dividend_date"))
    if fiscal_year is None:
        logger.debug(
            "Stock %s: dividend present but no valid date — skipping dividend persistence",
            data.get("symbol"),
        )
        return None

    net_amount = Decimal(str(net_amount_raw))
    # BOC only publishes net dividend; gross is unknown at ingestion time
    gross_amount = net_amount

    payment_date: Optional[date] = None
    div_date_iso = data.get("dividend_date")
    if div_date_iso:
        try:
            payment_date = date.fromisoformat(div_date_iso)
        except ValueError:
            payment_date = None

    existing = session.exec(
        select(Dividend)
        .where(Dividend.stock_id == stock_id)
        .where(Dividend.fiscal_year == fiscal_year)
    ).first()

    if existing:
        existing.net_amount = net_amount
        existing.gross_amount = gross_amount
        existing.payment_date = payment_date
        existing.is_confirmed = True
        session.add(existing)
        return existing

    dividend = Dividend(
        stock_id=stock_id,
        fiscal_year=fiscal_year,
        gross_amount=gross_amount,
        net_amount=net_amount,
        payment_date=payment_date,
        is_confirmed=True,
    )
    session.add(dividend)
    return dividend


# ── Main orchestrator ─────────────────────────────────────────────────────────

def process_boc(
    session: Session,
    pdf_path: Path,
    target_date: date,
    force: bool = False,
) -> int:
    """
    Parse a BOC PDF and persist all stock data atomically.

    Args:
        session: Active SQLModel session.
        pdf_path: Path to the BOC PDF file.
        target_date: Trading date the BOC corresponds to.
        force: If True, re-process even if already completed for that date.

    Returns:
        Number of stocks successfully persisted.

    Raises:
        NoDataError: If the parser returned no valid stock data.
        BocParseError: If parsing failed for an unexpected reason.
    """
    if not force and is_boc_run_completed(session, target_date):
        logger.info(
            "BOC for %s already processed — skipping (use force=True to re-process)",
            target_date,
        )
        existing_run = session.exec(
            select(BocRun).where(BocRun.run_date == target_date)
        ).first()
        return existing_run.stocks_parsed if existing_run else 0

    start_boc_run(session, target_date)

    try:
        parsed_stocks = parse_stocks_from_pdf(pdf_path, target_date)
    except Exception as exc:
        mark_boc_run_failed(session, target_date, f"Parser crashed: {exc}")
        raise BocParseError(str(exc)) from exc

    if not parsed_stocks:
        mark_boc_run_failed(session, target_date, "No valid stocks parsed")
        raise NoDataError()

    persisted = 0
    try:
        for data in parsed_stocks:
            stock = upsert_stock(session, data)
            upsert_daily_price(session, stock.id, data, target_date)
            upsert_dividend(session, stock.id, data)
            persisted += 1
        session.commit()
    except Exception as exc:
        session.rollback()
        mark_boc_run_failed(session, target_date, f"DB write failed: {exc}")
        raise

    mark_boc_run_success(session, target_date, stocks_parsed=persisted)
    logger.info(
        "process_boc complete for %s — %d stocks persisted",
        target_date, persisted,
    )
    return persisted
