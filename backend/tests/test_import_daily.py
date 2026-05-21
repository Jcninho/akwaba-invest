"""
Unit tests for scripts/import_daily.py

All tests are pure — no DB, no network, no files.
Parsing functions are exercised against the exact TSV payloads
defined in STOCKS_TEXT, INDICES_TEXT, DIVIDENDS_TEXT below.
"""
import pytest
from datetime import date

from scripts.import_daily import (
    build_json,
    parse_date_fr,
    parse_dividends,
    parse_indices,
    parse_number,
    parse_pct,
    parse_stocks,
    resolve_symbol,
)

# ---------------------------------------------------------------------------
# Canonical test fixtures — exact data from the task specification
# ---------------------------------------------------------------------------

STOCKS_TEXT = (
    "Nom\tOuverture\t+Haut\t+Bas\tVolume (titres)\tVolume (XOF)\tDernier\tVariation\n"
    "AFRICA GLOBAL LOGISTICS\t1 745\t1 745\t1 690\t60 305\t101 915 450\t1 690\t2.42%\n"
    "BANK OF AFRICA BENIN\t9 410\t9 420\t9 410\t5 259\t49 539 780\t9 420\t0.16%\n"
    "SONATEL\t28 850\t28 900\t28 850\t8 016\t231 662 400\t28 900\t0.17%\n"
    "MOVIS CI\t2 395\t2 395\t2 395\t0\t0\t2 395\t0.00%\n"
    "UNILEVER CI\t60 000\t60 000\t59 900\t6\t359 400\t59 900\t3.28%"
)

INDICES_TEXT = (
    "Nom\tOuverture\t+Haut\t+Bas\tDernier\tVariation\n"
    "BRVM - AGRICULTURE\t341.63\t341.63\t341.63\t341.63\t3.07%\n"
    "BRVM - CONSOMMATION DE BASE\t266.28\t266.28\t266.28\t266.28\t2.25%\n"
    "BRVM 30\t197.55\t197.55\t197.55\t197.55\t0.41%\n"
    "BRVM COMPOSITE\t421.55\t421.55\t421.55\t421.55\t0.81%\n"
    "Capitalisation BRVM\t16 111 022\t16 111 022\t16 111 022\t16 111 022\t0.50%"
)

DIVIDENDS_TEXT = (
    "Date détachement\tNom\tMontant\tRendement\n"
    "22/05/2026\tSONATEL\t1740,00\t6,02 %\n"
    "A préciser\tSMB CI\t704,00\t5,46 %\n"
    "29/05/2026\tBANK OF AFRICA SENEGAL\t450,00\t5,63 %"
)

_TRADING_DATE = date(2026, 5, 21)


# ===========================================================================
# parse_number
# ===========================================================================

def test_parse_number_french_thousands():
    assert parse_number("28 900") == 28900.0
    assert parse_number("16 111 022") == 16111022.0
    assert parse_number("101 915 450") == 101915450.0


def test_parse_number_decimal_comma():
    assert parse_number("421,55") == 421.55
    assert parse_number("1 740,00") == 1740.0
    assert parse_number("341.63") == 341.63  # period also works


def test_parse_number_none_for_empty():
    assert parse_number("") is None
    assert parse_number("-") is None
    assert parse_number("A préciser") is None
    assert parse_number("  ") is None


# ===========================================================================
# parse_pct
# ===========================================================================

def test_parse_pct_with_percent_sign():
    assert parse_pct("0.17%") == pytest.approx(0.17)
    assert parse_pct("2.42%") == pytest.approx(2.42)
    assert parse_pct("0.00%") == pytest.approx(0.0)


def test_parse_pct_french_comma():
    assert parse_pct("0,81 %") == pytest.approx(0.81)
    assert parse_pct("6,02 %") == pytest.approx(6.02)
    assert parse_pct("3,07%") == pytest.approx(3.07)


def test_parse_pct_negative():
    assert parse_pct("-2.33%") == pytest.approx(-2.33)
    assert parse_pct("-0,50 %") == pytest.approx(-0.50)


# ===========================================================================
# parse_date_fr
# ===========================================================================

def test_parse_date_fr_valid():
    assert parse_date_fr("22/05/2026") == "2026-05-22"
    assert parse_date_fr("29/05/2026") == "2026-05-29"
    assert parse_date_fr("01/01/2025") == "2025-01-01"


def test_parse_date_fr_a_preciser_returns_none():
    assert parse_date_fr("A préciser") is None
    assert parse_date_fr("") is None
    assert parse_date_fr("  ") is None


# ===========================================================================
# resolve_symbol
# ===========================================================================

def test_resolve_symbol_known_name():
    assert resolve_symbol("SONATEL") == "SNTS"
    assert resolve_symbol("AFRICA GLOBAL LOGISTICS") == "SDSC"
    assert resolve_symbol("BANK OF AFRICA BENIN") == "BOAB"
    assert resolve_symbol("UNILEVER CI") == "UNLC"
    # Case-insensitive
    assert resolve_symbol("sonatel") == "SNTS"
    assert resolve_symbol("  SONATEL  ") == "SNTS"


def test_resolve_symbol_delisted_returns_none():
    assert resolve_symbol("MOVIS CI") is None


def test_resolve_symbol_unknown_raises():
    with pytest.raises(ValueError, match="Unknown company name"):
        resolve_symbol("TOTALLY UNKNOWN COMPANY XYZ")


# ===========================================================================
# parse_stocks
# ===========================================================================

def test_parse_stocks_count():
    """4 valid stocks — MOVIS CI (delisted) skipped, header line skipped."""
    stocks = parse_stocks(STOCKS_TEXT, _TRADING_DATE)
    assert len(stocks) == 4


def test_parse_stocks_sonatel_values():
    stocks = parse_stocks(STOCKS_TEXT, _TRADING_DATE)
    snts = next(s for s in stocks if s["symbol"] == "SNTS")

    assert snts["close"] == pytest.approx(28900.0)
    assert snts["open"] == pytest.approx(28850.0)
    assert snts["high"] == pytest.approx(28900.0)
    assert snts["low"] == pytest.approx(28850.0)
    assert snts["volume_units"] == 8016
    assert snts["volume_xof"] == 231662400
    assert snts["variation_pct"] == pytest.approx(0.17)
    assert snts["trading_date"] == "2026-05-21"


def test_parse_stocks_movis_skipped():
    stocks = parse_stocks(STOCKS_TEXT, _TRADING_DATE)
    symbols = [s["symbol"] for s in stocks]
    assert "MOVIS CI" not in symbols          # raw name absent
    # None should never appear as a symbol
    assert None not in symbols


# ===========================================================================
# parse_indices
# ===========================================================================

def test_parse_indices_composite():
    indices = parse_indices(INDICES_TEXT)
    assert "brvm_composite" in indices
    entry = indices["brvm_composite"]
    assert entry["value"] == pytest.approx(421.55)
    assert entry["variation_pct"] == pytest.approx(0.81)


def test_parse_indices_capitalisation():
    indices = parse_indices(INDICES_TEXT)
    assert "capitalisation_fcfa" in indices
    # Capitalisation is stored as a scalar, not a dict
    cap = indices["capitalisation_fcfa"]
    assert isinstance(cap, float)
    assert cap == pytest.approx(16111022.0)


def test_parse_indices_agriculture_in_sectoriels():
    """Agriculture is a sector index — build_json puts it in sectoriels."""
    indices = parse_indices(INDICES_TEXT)
    # parse_indices returns a flat dict including brvm_agriculture
    assert "brvm_agriculture" in indices

    # After build_json, non-main indices appear under sectoriels
    result = build_json([], indices, [], _TRADING_DATE)
    assert "brvm_agriculture" in result["indices"]["sectoriels"]
    agri = result["indices"]["sectoriels"]["brvm_agriculture"]
    assert agri["value"] == pytest.approx(341.63)
    assert agri["variation_pct"] == pytest.approx(3.07)


# ===========================================================================
# parse_dividends
# ===========================================================================

def test_parse_dividends_with_date():
    divs = parse_dividends(DIVIDENDS_TEXT)
    snts = next(d for d in divs if d["symbol"] == "SNTS")

    assert snts["date_detachement"] == "2026-05-22"
    assert snts["montant_net"] == pytest.approx(1740.0)
    assert snts["rendement_pct"] == pytest.approx(6.02)


def test_parse_dividends_a_preciser_date_none():
    divs = parse_dividends(DIVIDENDS_TEXT)
    smbc = next(d for d in divs if d["symbol"] == "SMBC")

    assert smbc["date_detachement"] is None
    assert smbc["montant_net"] == pytest.approx(704.0)
    assert smbc["rendement_pct"] == pytest.approx(5.46)


# ===========================================================================
# build_json
# ===========================================================================

def test_build_json_structure():
    stocks = parse_stocks(STOCKS_TEXT, _TRADING_DATE)
    indices = parse_indices(INDICES_TEXT)
    dividends = parse_dividends(DIVIDENDS_TEXT)
    result = build_json(stocks, indices, dividends, _TRADING_DATE)

    # Top-level keys
    assert "metadata" in result
    assert "indices" in result
    assert "stocks" in result

    # Metadata fields
    meta = result["metadata"]
    assert meta["trading_date"] == "2026-05-21"
    assert meta["source"] == "daily_import"
    assert meta["total_stocks"] == 4
    assert "generated_at" in meta


def test_build_json_dividend_attached_to_stock():
    stocks = parse_stocks(STOCKS_TEXT, _TRADING_DATE)
    indices = parse_indices(INDICES_TEXT)
    dividends = parse_dividends(DIVIDENDS_TEXT)
    result = build_json(stocks, indices, dividends, _TRADING_DATE)

    snts_entry = next(s for s in result["stocks"] if s["symbol"] == "SNTS")
    assert snts_entry["dividend"] is not None
    div = snts_entry["dividend"]
    assert div["montant_net"] == pytest.approx(1740.0)
    assert div["date_detachement"] == "2026-05-22"
    assert div["rendement_pct"] == pytest.approx(6.02)


def test_build_json_main_indices_not_in_sectoriels():
    indices = parse_indices(INDICES_TEXT)
    result = build_json([], indices, [], _TRADING_DATE)

    root_indices = result["indices"]
    sectoriels = root_indices.get("sectoriels", {})

    # Main indices must be at root level
    assert "brvm_composite" in root_indices
    assert "capitalisation_fcfa" in root_indices

    # Main indices must NOT appear in sectoriels
    assert "brvm_composite" not in sectoriels
    assert "brvm_30" not in sectoriels
    assert "capitalisation_fcfa" not in sectoriels
