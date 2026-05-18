import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_boc_pdf(pdf_path: Path, trading_date: date) -> list[dict]:
    # TODO: use pdfplumber to extract ticker, open, close, volume from BOC PDF
    # Return list of dicts: {"ticker": str, "open": Decimal, "close": Decimal, "volume": int}
    raise NotImplementedError


def extract_trading_date_from_pdf(pdf_path: Path) -> date:
    # TODO: parse the trading date printed on the BOC PDF header
    raise NotImplementedError


def normalize_ticker(raw_ticker: str) -> str:
    return raw_ticker.strip().upper()
