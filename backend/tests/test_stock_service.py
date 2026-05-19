"""Unit tests for stock_service with in-memory SQLite."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from app.models import Stock, DailyPrice, Dividend, BocRun
from app.services.stock_service import (
    upsert_stock,
    upsert_daily_price,
    upsert_dividend,
    process_boc,
    _derive_fiscal_year,
)
from app.utils.exceptions import NoDataError, BocParseError


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _sample_stock_data():
    """Returns a single parsed stock dict matching the BOC parser output."""
    return {
        "symbol": "SNTS",
        "name": "SONATEL SN",
        "sector": "TEL",
        "sector_name": "Télécommunications",
        "prev_close": 28900.0,
        "open": 28850.0,
        "price": 28800.0,
        "change_pct": -0.35,
        "volume": 14844,
        "value": 428648545,
        "ref_price": 28800.0,
        "yearly_change": 10.26,
        "dividend": 1655.0,
        "dividend_date": "2025-05-22",
        "dividend_yield": 5.75,
        "per": 6.96,
        "boc_date": "2026-05-18",
    }


# ── _derive_fiscal_year ───────────────────────────────────────────────────────

def test_derive_fiscal_year_valid():
    assert _derive_fiscal_year("2025-05-22") == 2025

def test_derive_fiscal_year_none():
    assert _derive_fiscal_year(None) is None

def test_derive_fiscal_year_invalid():
    assert _derive_fiscal_year("not-a-date") is None


# ── upsert_stock ──────────────────────────────────────────────────────────────

def test_upsert_stock_creates_new(session):
    data = _sample_stock_data()
    stock = upsert_stock(session, data)
    session.commit()
    assert stock.id is not None
    assert stock.symbol == "SNTS"
    assert stock.name == "SONATEL SN"
    assert stock.sector == "Télécommunications"


def test_upsert_stock_updates_existing(session):
    data = _sample_stock_data()
    s1 = upsert_stock(session, data)
    session.commit()

    data["name"] = "SONATEL SENEGAL"
    s2 = upsert_stock(session, data)
    session.commit()

    assert s1.id == s2.id
    assert s2.name == "SONATEL SENEGAL"


def test_upsert_stock_default_country(session):
    data = _sample_stock_data()
    stock = upsert_stock(session, data)
    session.commit()
    assert stock.country == "UEMOA"


# ── upsert_daily_price ────────────────────────────────────────────────────────

def test_upsert_daily_price_creates_new(session):
    data = _sample_stock_data()
    stock = upsert_stock(session, data)
    session.commit()

    price = upsert_daily_price(session, stock.id, data, date(2026, 5, 18))
    session.commit()

    assert price.id is not None
    assert price.close_price == Decimal("28800.0")
    assert price.volume == 14844
    assert price.variation_pct == Decimal("-0.35")


def test_upsert_daily_price_idempotent(session):
    data = _sample_stock_data()
    stock = upsert_stock(session, data)
    session.commit()

    p1 = upsert_daily_price(session, stock.id, data, date(2026, 5, 18))
    session.commit()
    p2 = upsert_daily_price(session, stock.id, data, date(2026, 5, 18))
    session.commit()

    assert p1.id == p2.id  # same row, no duplicate

    all_prices = session.exec(select(DailyPrice)).all()
    assert len(all_prices) == 1


def test_upsert_daily_price_updates_close_price(session):
    data = _sample_stock_data()
    stock = upsert_stock(session, data)
    session.commit()

    upsert_daily_price(session, stock.id, data, date(2026, 5, 18))
    session.commit()

    data["price"] = 29000.0
    p2 = upsert_daily_price(session, stock.id, data, date(2026, 5, 18))
    session.commit()

    assert p2.close_price == Decimal("29000.0")


def test_upsert_daily_price_handles_missing_optional_fields(session):
    data = _sample_stock_data()
    data["open"] = None
    data["change_pct"] = None
    data["volume"] = None

    stock = upsert_stock(session, data)
    session.commit()
    price = upsert_daily_price(session, stock.id, data, date(2026, 5, 18))
    session.commit()

    assert price.open_price is None
    assert price.variation_pct is None
    assert price.volume == 0


# ── upsert_dividend ───────────────────────────────────────────────────────────

def test_upsert_dividend_creates_new(session):
    data = _sample_stock_data()
    stock = upsert_stock(session, data)
    session.commit()

    div = upsert_dividend(session, stock.id, data)
    session.commit()

    assert div is not None
    assert div.fiscal_year == 2025
    assert div.net_amount == Decimal("1655.0")
    assert div.payment_date == date(2025, 5, 22)
    assert div.is_confirmed is True


def test_upsert_dividend_no_amount_returns_none(session):
    data = _sample_stock_data()
    data["dividend"] = None

    stock = upsert_stock(session, data)
    session.commit()
    div = upsert_dividend(session, stock.id, data)
    session.commit()

    assert div is None


def test_upsert_dividend_zero_amount_returns_none(session):
    data = _sample_stock_data()
    data["dividend"] = 0

    stock = upsert_stock(session, data)
    session.commit()
    div = upsert_dividend(session, stock.id, data)

    assert div is None


def test_upsert_dividend_no_date_returns_none(session):
    data = _sample_stock_data()
    data["dividend_date"] = None

    stock = upsert_stock(session, data)
    session.commit()
    div = upsert_dividend(session, stock.id, data)

    assert div is None


def test_upsert_dividend_idempotent(session):
    data = _sample_stock_data()
    stock = upsert_stock(session, data)
    session.commit()

    d1 = upsert_dividend(session, stock.id, data)
    session.commit()
    d2 = upsert_dividend(session, stock.id, data)
    session.commit()

    assert d1.id == d2.id
    all_divs = session.exec(select(Dividend)).all()
    assert len(all_divs) == 1


# ── process_boc ───────────────────────────────────────────────────────────────

def test_process_boc_success(session):
    """End-to-end with mocked parser returning 2 stocks."""
    mock_data = [
        _sample_stock_data(),
        {
            "symbol": "NTLC", "name": "NESTLE CI", "sector": "CB",
            "sector_name": "Consommation de Base",
            "price": 11950.0, "open": 11750.0, "change_pct": 1.70,
            "volume": 686, "value": 8064220,
            "dividend": 721.6, "dividend_date": "2025-08-18",
            "per": 14.31, "boc_date": "2026-05-18",
        },
    ]

    with patch("app.services.stock_service.parse_stocks_from_pdf", return_value=mock_data):
        count = process_boc(session, pdf_path=None, target_date=date(2026, 5, 18))

    assert count == 2
    assert len(session.exec(select(Stock)).all()) == 2
    assert len(session.exec(select(DailyPrice)).all()) == 2
    assert len(session.exec(select(Dividend)).all()) == 2

    run = session.exec(select(BocRun)).first()
    assert run.status == "success"
    assert run.stocks_parsed == 2


def test_process_boc_idempotent(session):
    """Running twice on same date should not duplicate."""
    mock_data = [_sample_stock_data()]

    with patch("app.services.stock_service.parse_stocks_from_pdf", return_value=mock_data):
        c1 = process_boc(session, pdf_path=None, target_date=date(2026, 5, 18))
        c2 = process_boc(session, pdf_path=None, target_date=date(2026, 5, 18))

    assert c1 == 1
    assert c2 == 1  # short-circuit returns count from boc_run
    assert len(session.exec(select(Stock)).all()) == 1
    assert len(session.exec(select(DailyPrice)).all()) == 1


def test_process_boc_force_reprocess(session):
    """force=True must bypass the completed check."""
    mock_data = [_sample_stock_data()]

    with patch("app.services.stock_service.parse_stocks_from_pdf", return_value=mock_data):
        process_boc(session, pdf_path=None, target_date=date(2026, 5, 18))

        # Modify data and force re-run
        mock_data[0]["price"] = 30000.0
        process_boc(session, pdf_path=None, target_date=date(2026, 5, 18), force=True)

    price = session.exec(select(DailyPrice)).first()
    assert price.close_price == Decimal("30000.0")


def test_process_boc_empty_parser_raises(session):
    with patch("app.services.stock_service.parse_stocks_from_pdf", return_value=[]):
        with pytest.raises(NoDataError):
            process_boc(session, pdf_path=None, target_date=date(2026, 5, 18))

    run = session.exec(select(BocRun)).first()
    assert run.status == "failed"


def test_process_boc_parser_crash_raises(session):
    with patch(
        "app.services.stock_service.parse_stocks_from_pdf",
        side_effect=Exception("PDF corrupted"),
    ):
        with pytest.raises(BocParseError):
            process_boc(session, pdf_path=None, target_date=date(2026, 5, 18))

    run = session.exec(select(BocRun)).first()
    assert run.status == "failed"
    assert "PDF corrupted" in run.error_message
