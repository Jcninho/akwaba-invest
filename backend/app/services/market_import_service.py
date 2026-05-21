"""
Market import service — orchestrates the full daily import pipeline.

Called by the FastAPI /admin/upload-daily endpoint and importable
from other services.  No FastAPI-specific code here.
"""
import json
import logging
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from sqlmodel import Session

# scripts/ is a package at the backend/ root level.
# When the app runs from backend/ (uvicorn app.main:app), it is importable directly.
from scripts.import_daily import (
    build_json,
    parse_dividends,
    parse_indices,
    parse_stocks,
)
from scripts.import_to_db import import_json_to_db

logger = logging.getLogger(__name__)

# backend/ directory, two levels up from app/services/
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def process_upload(
    stocks_text: Optional[str],
    indices_text: Optional[str],
    dividends_text: Optional[str],
    trading_date: date,
    session: Session,
    force: bool = False,
) -> Dict:
    """Run the full daily market-data import pipeline.

    Steps:
      1. Parse raw text via import_daily functions
      2. Build canonical JSON structure
      3. Persist JSON to data/json/brvm_YYYYMMDD.json (and latest.json)
      4. Write to PostgreSQL via import_json_to_db
      5. Return a summary dict

    Args:
        stocks_text:    Tab-separated stocks table (required — pass "" to skip).
        indices_text:   Tab-separated indices table (optional, pass None to skip).
        dividends_text: Tab-separated dividends table (optional, pass None to skip).
        trading_date:   The trading session date these figures correspond to.
        session:        Active SQLModel session (caller controls lifecycle).
        force:          Re-process even if boc_runs already shows success.

    Returns::

        {
            "status": "success",
            "trading_date": "2026-05-21",
            "stocks_parsed": 47,
            "stocks_written": 47,
            "indices_parsed": 5,
            "dividends_parsed": 23,
            "json_path": "data/json/brvm_20260521.json"
        }
    """
    # ── Step 1: parse ────────────────────────────────────────────────────────
    stocks: List[Dict] = (
        parse_stocks(stocks_text, trading_date) if stocks_text else []
    )
    indices: Dict = parse_indices(indices_text) if indices_text else {}
    dividends: List[Dict] = parse_dividends(dividends_text) if dividends_text else []

    logger.info(
        "process_upload parsed: stocks=%d indices=%d dividends=%d for %s",
        len(stocks),
        len(indices),
        len(dividends),
        trading_date,
    )

    # ── Step 2: build JSON ───────────────────────────────────────────────────
    data = build_json(stocks, indices, dividends, trading_date)

    # ── Step 3: persist JSON to disk ─────────────────────────────────────────
    json_dir = _BACKEND_DIR / "data" / "json"
    json_dir.mkdir(parents=True, exist_ok=True)

    date_str = trading_date.strftime("%Y%m%d")
    json_path = json_dir / f"brvm_{date_str}.json"
    latest_path = json_dir / "latest.json"

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    with open(latest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    logger.info("JSON persisted to %s", json_path)

    # ── Step 4: write to PostgreSQL ──────────────────────────────────────────
    stocks_written = import_json_to_db(session, data, force=force)

    # ── Step 5: return summary ───────────────────────────────────────────────
    return {
        "status": "success",
        "trading_date": trading_date.isoformat(),
        "stocks_parsed": len(stocks),
        "stocks_written": stocks_written,
        "indices_parsed": len(indices),
        "dividends_parsed": len(dividends),
        "json_path": str(json_path),
    }
