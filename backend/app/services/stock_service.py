"""
Stock service — orchestrates BOC parsing and PostgreSQL persistence,
plus read-side query functions used by the /stocks API routes.

Core responsibility (write path): take a parsed stock dict from
boc_parser and write it into stocks, daily_prices, and dividends
tables atomically.

Query functions (read path): return plain dicts or SQLModel objects;
no FastAPI dependency — pure business/data-retrieval logic.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import BocRun, DailyPrice, Dividend, Financial, Stock
from app.services.boc_run_service import (
    is_boc_run_completed,
    mark_boc_run_failed,
    mark_boc_run_success,
    start_boc_run,
)
from app.utils.boc_parser import parse_stocks_from_pdf
from app.utils.exceptions import BocParseError, NoDataError, StockNotFoundError

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


# ── Read-side helpers ─────────────────────────────────────────────────────────

def _to_stock_with_price_dict(
    stock: Stock,
    price: Optional[DailyPrice],
) -> Dict[str, Any]:
    """Merge a Stock and optional DailyPrice into a flat dict for StockWithPrice."""
    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "sector": stock.sector,
        "close_price": price.close_price if price else None,
        "open_price": price.open_price if price else None,
        "high_price": price.high_price if price else None,
        "low_price": price.low_price if price else None,
        "volume": price.volume if price else None,
        "variation_pct": price.variation_pct if price else None,
        "trading_date": price.trading_date if price else None,
    }


def _fetch_stocks_with_price(
    session: Session,
    latest_date: Optional[date],
    *,
    sector: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Internal helper — join stocks + daily_prices on latest_date.

    Uses LEFT OUTER JOIN so stocks with no price row on that date are
    still returned (with None price fields). When latest_date is None
    (empty DB), returns all stocks with no price data.
    """
    if latest_date is None:
        stmt = select(Stock).where(Stock.is_active == True)  # noqa: E712
        if sector:
            stmt = stmt.where(Stock.sector == sector)
        stocks = session.exec(stmt).all()
        return [_to_stock_with_price_dict(s, None) for s in stocks]

    stmt = (
        select(Stock, DailyPrice)
        .outerjoin(
            DailyPrice,
            (DailyPrice.stock_id == Stock.id)
            & (DailyPrice.trading_date == latest_date),
        )
        .where(Stock.is_active == True)  # noqa: E712
    )
    if sector:
        stmt = stmt.where(Stock.sector == sector)
    if limit:
        stmt = stmt.limit(limit)

    rows = session.exec(stmt).all()
    return [_to_stock_with_price_dict(s, p) for s, p in rows]


# ── Public query functions ────────────────────────────────────────────────────


def get_latest_trading_date(session: Session) -> Optional[date]:
    """Return the most recent trading_date in daily_prices, or None if empty."""
    return session.exec(select(func.max(DailyPrice.trading_date))).first()


def get_all_stocks_with_latest_price(session: Session) -> List[Dict[str, Any]]:
    """
    Return all active stocks with their latest daily price.

    Joins stocks + daily_prices on the most recent global trading_date.
    """
    latest_date = get_latest_trading_date(session)
    return _fetch_stocks_with_price(session, latest_date)


def get_stock_detail(session: Session, symbol: str) -> Dict[str, Any]:
    """
    Return full stock detail: stock info + latest price + latest dividend.

    Raises:
        StockNotFoundError: if the symbol doesn't exist in the database.
    """
    stock = session.exec(
        select(Stock).where(Stock.symbol == symbol)
    ).first()
    if not stock:
        raise StockNotFoundError(symbol)

    latest_price = session.exec(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock.id)
        .order_by(DailyPrice.trading_date.desc())
        .limit(1)
    ).first()

    latest_dividend = session.exec(
        select(Dividend)
        .where(Dividend.stock_id == stock.id)
        .order_by(Dividend.fiscal_year.desc())
        .limit(1)
    ).first()

    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "sector": stock.sector,
        "country": stock.country,
        "latest_price": latest_price,
        "latest_dividend": latest_dividend,
    }


def get_top_movers(
    session: Session,
    n: int = 5,
    trading_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Return top n gainers and top n losers for trading_date.

    If trading_date is None, uses the most recent available date.
    Stocks with no variation_pct are excluded from both lists.

    Returns:
        {"gainers": [...], "losers": [...], "trading_date": date | None}
    """
    if trading_date is None:
        trading_date = get_latest_trading_date(session)

    if trading_date is None:
        return {"gainers": [], "losers": [], "trading_date": None}

    base = (
        select(Stock, DailyPrice)
        .join(DailyPrice, DailyPrice.stock_id == Stock.id)
        .where(DailyPrice.trading_date == trading_date)
        .where(DailyPrice.variation_pct.is_not(None))
    )

    gainers_rows = session.exec(
        base.order_by(DailyPrice.variation_pct.desc()).limit(n)
    ).all()
    losers_rows = session.exec(
        base.order_by(DailyPrice.variation_pct.asc()).limit(n)
    ).all()

    return {
        "gainers": [_to_stock_with_price_dict(s, p) for s, p in gainers_rows],
        "losers": [_to_stock_with_price_dict(s, p) for s, p in losers_rows],
        "trading_date": trading_date,
    }


def get_market_summary(session: Session) -> Dict[str, Any]:
    """
    Return dashboard summary:
    - trading_date (latest)
    - total active stocks
    - stocks_up / stocks_down / stocks_unchanged
    - top 5 gainers and losers
    """
    latest_date = get_latest_trading_date(session)
    total_stocks: int = session.exec(
        select(func.count(Stock.id)).where(Stock.is_active == True)  # noqa: E712
    ).one()

    if latest_date is None:
        return {
            "trading_date": None,
            "total_stocks": total_stocks,
            "stocks_up": 0,
            "stocks_down": 0,
            "stocks_unchanged": total_stocks,
            "top_gainers": [],
            "top_losers": [],
        }

    prices_rows = session.exec(
        select(Stock, DailyPrice)
        .join(DailyPrice, DailyPrice.stock_id == Stock.id)
        .where(DailyPrice.trading_date == latest_date)
    ).all()

    stocks_up = sum(
        1 for _, p in prices_rows
        if p.variation_pct is not None and p.variation_pct > 0
    )
    stocks_down = sum(
        1 for _, p in prices_rows
        if p.variation_pct is not None and p.variation_pct < 0
    )
    stocks_unchanged = total_stocks - stocks_up - stocks_down

    # Sort by variation_pct for top movers (exclude None)
    sortable = [
        (s, p) for s, p in prices_rows if p.variation_pct is not None
    ]
    sortable.sort(key=lambda x: float(x[1].variation_pct), reverse=True)

    top_gainers = [_to_stock_with_price_dict(s, p) for s, p in sortable[:5]]
    top_losers = [_to_stock_with_price_dict(s, p) for s, p in sortable[-5:][::-1]]

    return {
        "trading_date": latest_date,
        "total_stocks": total_stocks,
        "stocks_up": stocks_up,
        "stocks_down": stocks_down,
        "stocks_unchanged": stocks_unchanged,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
    }


def get_stocks_by_sector(
    session: Session, sector: str
) -> List[Dict[str, Any]]:
    """Return all active stocks in a given sector with their latest price."""
    latest_date = get_latest_trading_date(session)
    return _fetch_stocks_with_price(session, latest_date, sector=sector)


def search_stocks(session: Session, query: str) -> List[Dict[str, Any]]:
    """
    Search active stocks by symbol or name (case-insensitive, partial match).

    Returns at most 10 results, each with the latest price merged in.
    """
    latest_date = get_latest_trading_date(session)

    pattern = f"%{query}%"
    stmt = (
        select(Stock, DailyPrice)
        .outerjoin(
            DailyPrice,
            (DailyPrice.stock_id == Stock.id)
            & (DailyPrice.trading_date == latest_date),
        )
        .where(Stock.is_active == True)  # noqa: E712
        .where(
            Stock.symbol.ilike(pattern) | Stock.name.ilike(pattern)
        )
        .limit(10)
    )
    rows = session.exec(stmt).all()
    return [_to_stock_with_price_dict(s, p) for s, p in rows]


def get_price_history(
    session: Session, symbol: str, days: int = 30
) -> List[DailyPrice]:
    """
    Return daily price rows for a stock for the last `days` calendar days,
    measured back from the most recent available trading date.

    Raises:
        StockNotFoundError: if the symbol doesn't exist.
    """
    stock = session.exec(
        select(Stock).where(Stock.symbol == symbol)
    ).first()
    if not stock:
        raise StockNotFoundError(symbol)

    latest_date = get_latest_trading_date(session)
    if latest_date is None:
        return []

    cutoff = latest_date - timedelta(days=days)
    return session.exec(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock.id)
        .where(DailyPrice.trading_date >= cutoff)
        .order_by(DailyPrice.trading_date.desc())
    ).all()


def get_dividend_history(
    session: Session, symbol: str
) -> List[Dividend]:
    """
    Return all dividend rows for a stock, ordered newest first.

    Raises:
        StockNotFoundError: if the symbol doesn't exist.
    """
    stock = session.exec(
        select(Stock).where(Stock.symbol == symbol)
    ).first()
    if not stock:
        raise StockNotFoundError(symbol)

    return session.exec(
        select(Dividend)
        .where(Dividend.stock_id == stock.id)
        .order_by(Dividend.fiscal_year.desc())
    ).all()


def get_financial_history(
    session: Session, symbol: str
) -> List[Financial]:
    """
    Return all financial rows for a stock, ordered newest first.

    Raises:
        StockNotFoundError: if the symbol doesn't exist.
    """
    stock = session.exec(
        select(Stock).where(Stock.symbol == symbol)
    ).first()
    if not stock:
        raise StockNotFoundError(symbol)

    return session.exec(
        select(Financial)
        .where(Financial.stock_id == stock.id)
        .order_by(Financial.fiscal_year.desc())
    ).all()
