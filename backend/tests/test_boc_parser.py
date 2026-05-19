"""Unit tests for BOC parser pure functions."""
import pytest
from datetime import date
from app.utils.boc_parser import (
    parse_price, parse_pct, parse_int, parse_date,
    validate_stock, parse_stock_row, SECTOR_CODES,
)


# ── parse_price ───────────────────────────────────────────────────────────────

def test_parse_price_french_thousands():
    assert parse_price("15 000") == 15000.0

def test_parse_price_decimal_comma():
    assert parse_price("13,47") == 13.47

def test_parse_price_mixed():
    assert parse_price("15 050,50") == 15050.50

def test_parse_price_nbsp():
    assert parse_price("864,72") == 864.72

def test_parse_price_empty():
    assert parse_price("") is None

def test_parse_price_nc():
    assert parse_price("NC") is None

def test_parse_price_garbage():
    assert parse_price("abc") is None


# ── parse_pct ─────────────────────────────────────────────────────────────────

def test_parse_pct_positive():
    assert parse_pct("+7,47 %") == 7.47

def test_parse_pct_negative():
    assert parse_pct("-0,33 %") == -0.33

def test_parse_pct_zero():
    assert parse_pct("0,00 %") == 0.0

def test_parse_pct_no_sign():
    assert parse_pct("6,22 %") == 6.22

def test_parse_pct_nc():
    assert parse_pct("NC") is None


# ── parse_int ─────────────────────────────────────────────────────────────────

def test_parse_int_thousands():
    assert parse_int("1 336") == 1336

def test_parse_int_large():
    assert parse_int("20 069 970") == 20069970

def test_parse_int_empty():
    assert parse_int("") is None


# ── parse_date ────────────────────────────────────────────────────────────────

def test_parse_date_august():
    assert parse_date("18-août-25") == "2025-08-18"

def test_parse_date_september_abbr():
    assert parse_date("30-sept.-25") == "2025-09-30"

def test_parse_date_july_abbr():
    assert parse_date("07-juil.-25") == "2025-07-07"

def test_parse_date_april():
    assert parse_date("23-avr.-26") == "2026-04-23"

def test_parse_date_june():
    assert parse_date("04-juin-25") == "2025-06-04"

def test_parse_date_unknown_month():
    assert parse_date("18-xyz-25") is None

def test_parse_date_invalid_format():
    assert parse_date("not a date") is None


# ── validate_stock ────────────────────────────────────────────────────────────

def test_validate_stock_valid():
    stock = {"symbol": "SNTS", "price": 28800.0, "change_pct": -0.35}
    assert validate_stock(stock) is True

def test_validate_stock_no_symbol():
    stock = {"symbol": "", "price": 100.0}
    assert validate_stock(stock) is False

def test_validate_stock_zero_price():
    stock = {"symbol": "SNTS", "price": 0}
    assert validate_stock(stock) is False

def test_validate_stock_negative_price():
    stock = {"symbol": "SNTS", "price": -10}
    assert validate_stock(stock) is False

def test_validate_stock_change_too_high():
    stock = {"symbol": "SNTS", "price": 100.0, "change_pct": 150.0}
    assert validate_stock(stock) is False


# ── parse_stock_row ───────────────────────────────────────────────────────────

def test_parse_stock_row_sonatel():
    """Real row from BOC 18/05/2026: SONATEL."""
    row = [
        "TEL", "SNTS", "SONATEL SN", "",
        "28 900", "28 850", "28 800", "-0,35 %",
        "14 844", "428 648 545", "28 800", "10,26 %",
        "1655", "22-mai-25", "5,75 %", "6,96",
    ]
    result = parse_stock_row(row, date(2026, 5, 18))
    assert result is not None
    assert result["symbol"] == "SNTS"
    assert result["name"] == "SONATEL SN"
    assert result["sector"] == "TEL"
    assert result["sector_name"] == "Télécommunications"
    assert result["price"] == 28800.0
    assert result["change_pct"] == -0.35
    assert result["volume"] == 14844
    assert result["dividend"] == 1655.0
    assert result["dividend_date"] == "2025-05-22"
    assert result["dividend_yield"] == 5.75
    assert result["per"] == 6.96
    assert result["boc_date"] == "2026-05-18"

def test_parse_stock_row_header_skipped():
    row = ["Code", "Symbole", "Titre", "", "Cours", "", "", "", "", "", "", "", "", "", "", ""]
    assert parse_stock_row(row, date(2026, 5, 18)) is None

def test_parse_stock_row_total_skipped():
    row = ["", "TOTAL", "", "", "", "", "", "", "1 116 268", "1 504 073 131", "", "", "", "", "", ""]
    assert parse_stock_row(row, date(2026, 5, 18)) is None

def test_parse_stock_row_compartiment_skipped():
    row = ["", "COMPARTIMENT PRESTIGE", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
    assert parse_stock_row(row, date(2026, 5, 18)) is None

def test_parse_stock_row_too_short():
    row = ["TEL", "SNTS", "SONATEL"]
    assert parse_stock_row(row, date(2026, 5, 18)) is None

def test_parse_stock_row_multiline_name():
    """Real case: name split across 2 lines like 'NSIA BANQUE COTE\\nD'IVOIRE'."""
    row = [
        "FIN", "NSBC", "NSIA BANQUE COTE\nD'IVOIRE", "",
        "15 000", "15 100", "15 650", "4,33 %",
        "4 875", "74 576 125", "15 650", "36,74 %",
        "668,15", "9-juil.-25", "4,27 %", "9,51",
    ]
    result = parse_stock_row(row, date(2026, 5, 18))
    assert result is not None
    assert result["name"] == "NSIA BANQUE COTE D'IVOIRE"


# ── SECTOR_CODES ──────────────────────────────────────────────────────────────

def test_all_sectors_in_bocs_18_may_2026_are_mapped():
    """All 7 sector codes from BOC 18/05/2026 must be in SECTOR_CODES."""
    expected = {"TEL", "FIN", "CB", "CD", "IND", "ENE", "SPU"}
    assert expected.issubset(SECTOR_CODES.keys())
