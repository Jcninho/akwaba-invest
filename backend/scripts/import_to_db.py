"""
Import JSON market data file into PostgreSQL.

Reads a brvm_YYYYMMDD.json (or latest.json) produced by import_daily.py
and writes stocks, daily_prices, and dividends atomically.
The run is recorded in boc_runs for idempotency.

Usage:
    python scripts/import_to_db.py --file data/json/brvm_20260521.json
    python scripts/import_to_db.py --file data/json/latest.json --force
"""
import argparse
import json
import logging
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure backend/ is in PYTHONPATH so "from app.xxx" imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.database as _database  # access engine at call time for monkeypatching
from sqlmodel import Session, select

from app.models import BocRun, DailyPrice, Dividend, Stock
from app.services.boc_run_service import (
    get_boc_run,
    is_boc_run_completed,
    mark_boc_run_failed,
    mark_boc_run_success,
    start_boc_run,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal upsert helpers (not part of the public API)
# ---------------------------------------------------------------------------

def _upsert_stock(session: Session, symbol: str) -> Stock:
    """Look up stock by symbol.  Create a minimal placeholder if absent.

    Daily import data does not carry company metadata (name, sector, country).
    The BOC pipeline populates those fields — we just ensure the row exists.
    """
    existing = session.exec(select(Stock).where(Stock.symbol == symbol)).first()
    if existing:
        return existing

    stock = Stock(
        symbol=symbol,
        name=symbol,  # placeholder until overwritten by BOC import
        sector="",
        country="UEMOA",
        is_active=True,
    )
    session.add(stock)
    session.flush()  # obtain stock.id before returning
    logger.debug("Created placeholder stock row for symbol=%s", symbol)
    return stock


def _upsert_daily_price(
    session: Session,
    stock_id: int,
    stock_data: Dict[str, Any],
    trading_date: date,
) -> DailyPrice:
    """Create or update the daily_price row for (stock_id, trading_date).

    Maps JSON fields → DailyPrice columns:
      close        → close_price
      open         → open_price
      high         → high_price
      low          → low_price
      volume_units → volume
      variation_pct→ variation_pct
    (volume_xof is stored in JSON only — no DB column)
    """
    existing = session.exec(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock_id)
        .where(DailyPrice.trading_date == trading_date)
    ).first()

    close_raw = stock_data.get("close")
    open_raw = stock_data.get("open")
    high_raw = stock_data.get("high")
    low_raw = stock_data.get("low")
    vol_units = stock_data.get("volume_units")
    var_pct = stock_data.get("variation_pct")

    close_price = Decimal(str(close_raw)) if close_raw is not None else Decimal("0")
    open_price = Decimal(str(open_raw)) if open_raw is not None else None
    high_price = Decimal(str(high_raw)) if high_raw is not None else None
    low_price = Decimal(str(low_raw)) if low_raw is not None else None
    volume = int(vol_units) if vol_units is not None else 0
    variation_pct = Decimal(str(var_pct)) if var_pct is not None else None

    if existing:
        existing.close_price = close_price
        existing.open_price = open_price
        existing.high_price = high_price
        existing.low_price = low_price
        existing.volume = volume
        existing.variation_pct = variation_pct
        session.add(existing)
        return existing

    price_row = DailyPrice(
        stock_id=stock_id,
        trading_date=trading_date,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
        variation_pct=variation_pct,
    )
    session.add(price_row)
    return price_row


def _upsert_dividend(
    session: Session,
    stock_id: int,
    dividend_data: Dict[str, Any],
) -> Optional[Dividend]:
    """Create or update a Dividend row for (stock_id, fiscal_year).

    fiscal_year is derived from date_detachement.
    Returns None if fiscal_year cannot be determined (date is None/invalid).
    """
    montant_net = dividend_data.get("montant_net")
    if montant_net is None:
        return None

    date_detachement_iso = dividend_data.get("date_detachement")
    if date_detachement_iso:
        try:
            fiscal_year: Optional[int] = int(date_detachement_iso.split("-")[0])
        except (ValueError, IndexError, AttributeError):
            fiscal_year = None
    else:
        fiscal_year = None

    if fiscal_year is None:
        logger.debug(
            "Dividend for stock_id=%d has no valid detachment date — skipping", stock_id
        )
        return None

    net_amount = Decimal(str(montant_net))
    gross_amount = net_amount  # gross is unknown from web data; BOC provides the net

    detachment_date: Optional[date] = None
    if date_detachement_iso:
        try:
            detachment_date = date.fromisoformat(date_detachement_iso)
        except ValueError:
            detachment_date = None

    existing = session.exec(
        select(Dividend)
        .where(Dividend.stock_id == stock_id)
        .where(Dividend.fiscal_year == fiscal_year)
    ).first()

    if existing:
        existing.net_amount = net_amount
        existing.gross_amount = gross_amount
        existing.detachment_date = detachment_date
        # Data from web — not yet confirmed by official BOC
        existing.is_confirmed = False
        session.add(existing)
        return existing

    dividend = Dividend(
        stock_id=stock_id,
        fiscal_year=fiscal_year,
        gross_amount=gross_amount,
        net_amount=net_amount,
        detachment_date=detachment_date,
        is_confirmed=False,
    )
    session.add(dividend)
    return dividend


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def import_json_to_db(session: Session, data: Dict, force: bool = False) -> int:
    """Write JSON market data into PostgreSQL.

    Steps:
      1. Check idempotency via boc_runs (skip if already done and not force)
      2. Upsert stocks (symbol as natural key)
      3. Upsert daily_prices (stock_id + trading_date as unique key)
      4. Upsert dividends when present (stock_id + fiscal_year as unique key)
      5. Record run status in boc_runs

    Args:
        session: Active SQLModel session.
        data:    Parsed JSON dict (output of build_json / import_daily.py).
        force:   Re-process even if boc_runs shows success for that date.

    Returns:
        Number of stock rows written.

    Raises:
        Exception: DB write failure (session is rolled back before raising).
    """
    trading_date = date.fromisoformat(data["metadata"]["trading_date"])

    if not force and is_boc_run_completed(session, trading_date):
        logger.info(
            "Import for %s already completed — skipping (use force=True to re-process)",
            trading_date,
        )
        existing_run = get_boc_run(session, trading_date)
        return existing_run.stocks_parsed if existing_run else 0

    start_boc_run(session, trading_date)

    persisted = 0
    try:
        for stock_data in data.get("stocks", []):
            symbol = stock_data["symbol"]
            stock = _upsert_stock(session, symbol)
            _upsert_daily_price(session, stock.id, stock_data, trading_date)

            dividend_data = stock_data.get("dividend")
            if dividend_data:
                _upsert_dividend(session, stock.id, dividend_data)

            persisted += 1

        session.commit()

    except Exception as exc:
        session.rollback()
        mark_boc_run_failed(session, trading_date, f"DB write failed: {exc}")
        raise

    mark_boc_run_success(session, trading_date, stocks_parsed=persisted)
    logger.info(
        "import_json_to_db complete for %s — %d stocks persisted",
        trading_date,
        persisted,
    )
    return persisted


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Akwaba Invest — daily JSON → PostgreSQL import",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--file",
        type=str,
        required=True,
        help="Path to the brvm_YYYYMMDD.json file to import",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process even if boc_runs already shows success for that date",
    )
    args = parser.parse_args()

    _setup_logging()

    json_path = Path(args.file)
    if not json_path.exists():
        logger.error("File not found: %s", args.file)
        return 1

    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)

    trading_date = data.get("metadata", {}).get("trading_date", "unknown")

    try:
        with Session(_database.engine) as session:
            count = import_json_to_db(session, data, force=args.force)
    except Exception:
        logger.exception("Import failed")
        print(f"RESULT: failed | date={trading_date} | stocks=0")
        return 1

    print(f"RESULT: success | date={trading_date} | stocks={count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
