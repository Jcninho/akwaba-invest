import pytest
from pathlib import Path

from app.utils.boc_parser import normalize_ticker, parse_boc_pdf


def test_normalize_ticker_strips_whitespace() -> None:
    assert normalize_ticker("  SGBCI  ") == "SGBCI"


def test_normalize_ticker_uppercases() -> None:
    assert normalize_ticker("sgbci") == "SGBCI"


def test_parse_boc_pdf_missing_file_raises() -> None:
    with pytest.raises(Exception):
        parse_boc_pdf(Path("/nonexistent/boc.pdf"), trading_date=None)
