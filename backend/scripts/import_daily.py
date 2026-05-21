"""
Daily market data import pipeline.

Parses tab-separated market data (stocks, indices, dividends)
and generates a structured JSON file for downstream consumption.

Usage:
    # Stocks only
    python scripts/import_daily.py --stocks data/stocks.txt --date 2026-05-21

    # Stocks + indices
    python scripts/import_daily.py --stocks data/stocks.txt \\
        --indices data/indices.txt --date 2026-05-21

    # All three sources
    python scripts/import_daily.py --stocks data/stocks.txt \\
        --indices data/indices.txt --dividends data/dividends.txt \\
        --date 2026-05-21

    # Output to specific directory
    python scripts/import_daily.py --stocks data/stocks.txt
        --date 2026-05-21 --output data/json/
"""
import argparse
import json
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/scripts/ -> backend/

# ---------------------------------------------------------------------------
# Company name → BOC symbol mapping
# None = delisted company (skip silently)
# ---------------------------------------------------------------------------
NAME_TO_SYMBOL: Dict[str, Optional[str]] = {
    "AFRICA GLOBAL LOGISTICS": "SDSC",
    "AFRICA GLOBAL LOGISTICS CI": "SDSC",
    "BANK OF AFRICA BENIN": "BOAB",
    "BANK OF AFRICA BN": "BOAB",
    "BANK OF AFRICA BURKINA FASO": "BOABF",
    "BANK OF AFRICA BF": "BOABF",
    "BANK OF AFRICA CI": "BOAC",
    "BANK OF AFRICA MALI": "BOAM",
    "BANK OF AFRICA ML": "BOAM",
    "BANK OF AFRICA NIGER": "BOAN",
    "BANK OF AFRICA NG": "BOAN",
    "BANK OF AFRICA SENEGAL": "BOAS",
    "BANK OF AFRICA SN": "BOAS",
    "BANQUE INTERNATIONALE POUR LE COMMERCE DU BENIN": "BICB",
    "BIIC BN": "BICB",
    "BERNABE": "BNBC",
    "BERNABE CI": "BNBC",
    "BICICI": "BICC",
    "BICI CI": "BICC",
    "CFAO CI": "CFAC",
    "CFAO MOTORS CI": "CFAC",
    "CIE CI": "CIEC",
    "CORIS BANK INTERNATIONAL BF": "CBIBF",
    "CORIS BANK INTERNATIONAL": "CBIBF",
    "CROWN SIEM": "SEMC",
    "EVIOSYS PACKAGING SIEM CI": "SEMC",
    "ECOBANK CI": "ECOC",
    "ECOBANK COTE D'IVOIRE": "ECOC",
    "ERIUM": "SIVC",
    "ERIUM CI": "SIVC",
    "ETI TG": "ETIT",
    "ECOBANK TRANS. INCORP. TG": "ETIT",
    "FILTISAC CI": "FTSC",
    "LOTERIE NATIONALE DU BENIN": "LNBB",
    "NEI CEDA CI": "NEIC",
    "NEI-CEDA CI": "NEIC",
    "NESTLE CI": "NTLC",
    "NSIA BANQUE": "NSBC",
    "NSIA BANQUE COTE D'IVOIRE": "NSBC",
    "ONATEL BF": "ONTBF",
    "ORAGROUP TOGO": "ORGT",
    "ORANGE CI": "ORAC",
    "ORANGE COTE D'IVOIRE": "ORAC",
    "PALMCI": "PALC",
    "PALM CI": "PALC",
    "SAFCA CI": "SAFC",
    "SAPH CI": "SPHC",
    "SERVAIR ABIDJAN CI": "ABJC",
    "SETAO CI": "STAC",
    "SGBCI": "SGBC",
    "SOCIETE GENERALE COTE D'IVOIRE": "SGBC",
    "SICABLE CI": "CABC",
    "SICOR": "SICC",
    "SICOR CI": "SICC",
    "SITAB": "STBC",
    "SITAB CI": "STBC",
    "SMB CI": "SMBC",
    "SOCIETE IVOIRIENNE DE BANQUE CI": "SIBC",
    "SOCIETE IVOIRIENNE DE BANQUE": "SIBC",
    "SODECI": "SDCC",
    "SODE CI": "SDCC",
    "SOGB": "SOGC",
    "SOGB CI": "SOGC",
    "SOLIBRA CI": "SLBC",
    "SONATEL": "SNTS",
    "SONATEL SN": "SNTS",
    "SUCRIVOIRE": "SCRC",
    "TOTAL CI": "TTLC",
    "TOTALENERGIES MARKETING CI": "TTLC",
    "TOTAL SENEGAL": "TTLS",
    "TOTALENERGIES MARKETING SN": "TTLS",
    "TRACTAFRIC MOTORS CI": "PRSC",
    "UNILEVER CI": "UNLC",
    "UNIWAX CI": "UNXC",
    "VIVO ENERGY CI": "SHEC",
    # Delisted — ignore silently
    "MOVIS CI": None,
}

# ---------------------------------------------------------------------------
# Index name → internal key mapping
# ---------------------------------------------------------------------------
INDEX_NAME_MAP: Dict[str, str] = {
    "BRVM COMPOSITE": "brvm_composite",
    "BRVM 30": "brvm_30",
    "BRVM - PRESTIGE": "brvm_prestige",
    "BRVM PRESTIGE": "brvm_prestige",
    "BRVM - PRINCIPAL": "brvm_principal",
    "BRVM PRINCIPAL": "brvm_principal",
    "BRVM - AGRICULTURE": "brvm_agriculture",
    "BRVM - AUTRES SECTEURS": "brvm_autres_secteurs",
    "BRVM - CONSOMMATION DE BASE": "brvm_consommation_base",
    "BRVM - CONSOMMATION DISCRETIONNAIRE": "brvm_consommation_discretionnaire",
    "BRVM - DISTRIBUTION": "brvm_distribution",
    "BRVM - ENERGIE": "brvm_energie",
    "BRVM - FINANCE": "brvm_finance",
    "BRVM - INDUSTRIE": "brvm_industrie",
    "BRVM - INDUSTRIELS": "brvm_industriels",
    "BRVM - SERVICES FINANCIERS": "brvm_services_financiers",
    "BRVM - SERVICES PUBLICS": "brvm_services_publics",
    "BRVM - TELECOMMUNICATIONS": "brvm_telecommunications",
    "BRVM - TRANSPORT": "brvm_transport",
    "Capitalisation BRVM": "capitalisation_fcfa",
}

# Main indices that belong in the indices root (not in sectoriels)
_MAIN_INDICES = frozenset(
    {"brvm_composite", "brvm_30", "brvm_prestige", "brvm_principal", "capitalisation_fcfa"}
)

# Build a case-insensitive lookup for INDEX_NAME_MAP
_INDEX_MAP_UPPER: Dict[str, str] = {k.upper(): v for k, v in INDEX_NAME_MAP.items()}

# Pattern to detect valid dividend date fields
_DATE_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")


# ---------------------------------------------------------------------------
# Primitive parsers
# ---------------------------------------------------------------------------

def parse_number(value: str) -> Optional[float]:
    """Parse French-formatted number string.

    Handles:
      - "28 900"       → 28900.0   (spaces as thousand separators)
      - "421,55"       → 421.55    (comma as decimal)
      - "1 740,00"     → 1740.0
      - "16 111 022"   → 16111022.0
      - "341.63"       → 341.63    (period already a decimal)

    Returns None for empty strings, "-", "A préciser".
    """
    if not value:
        return None
    stripped = value.strip()
    if stripped in ("-", "A préciser", "N/A", ""):
        return None
    # Remove space and non-breaking space (used as thousand separators)
    cleaned = stripped.replace(" ", "").replace(" ", "").replace("\xa0", "")
    # Normalise decimal separator: replace comma with period
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_pct(value: str) -> Optional[float]:
    """Parse percentage string.

    Handles:
      - "0.17%"   → 0.17
      - "0,81 %"  → 0.81
      - "-2.33%"  → -2.33
      - "3,07%"   → 3.07
    """
    if not value:
        return None
    stripped = value.strip()
    if stripped in ("-", ""):
        return None
    # Remove percent sign and spaces, normalise decimal
    cleaned = stripped.replace("%", "").replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date_fr(value: str) -> Optional[str]:
    """Parse French date string to ISO 8601.

    Handles: "22/05/2026" → "2026-05-22"
    Returns None for "A préciser" or empty string.
    """
    if not value:
        return None
    stripped = value.strip()
    if stripped in ("A préciser", ""):
        return None
    try:
        parsed = datetime.strptime(stripped, "%d/%m/%Y")
        return parsed.date().isoformat()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Symbol resolution
# ---------------------------------------------------------------------------

def resolve_symbol(name: str) -> Optional[str]:
    """Map company name to BOC symbol.

    Returns:
        str  — the BOC ticker symbol
        None — company is delisted (e.g. MOVIS CI); caller should skip silently

    Raises:
        ValueError — name is completely unknown (not in mapping)
    """
    normalized = name.strip().upper()
    if normalized not in NAME_TO_SYMBOL:
        raise ValueError(f"Unknown company name: {name!r}")
    return NAME_TO_SYMBOL[normalized]


# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------

def parse_stocks(text: str, trading_date: date) -> List[Dict]:
    """Parse tab-separated stocks table.

    Expected column order:
        Nom | Ouverture | +Haut | +Bas | Volume (titres) | Volume (XOF) | Dernier | Variation

    Returns a list of dicts:
        {
            "symbol": "SNTS",
            "trading_date": "2026-05-21",
            "open": 28850.0,
            "high": 28900.0,
            "low": 28850.0,
            "close": 28900.0,
            "volume_units": 8016,
            "volume_xof": 231662400,
            "variation_pct": 0.17
        }

    Skips:
      - Lines with fewer than 3 columns
      - Header lines (first column == "Nom")
      - Delisted companies (None in NAME_TO_SYMBOL)
      - Truly unknown company names (logs warning, skips)
    """
    results: List[Dict] = []
    date_iso = trading_date.isoformat()

    for line in text.strip().splitlines():
        cols = line.split("\t")
        if len(cols) < 3:
            continue

        name = cols[0].strip()
        if name == "Nom":  # header line
            continue

        # Resolve symbol
        try:
            symbol = resolve_symbol(name)
        except ValueError:
            logger.warning("Unknown company name %r — skipping line", name)
            continue

        if symbol is None:
            # Delisted company — skip silently
            logger.debug("Delisted company %r — skipping", name)
            continue

        # Parse prices and volumes (columns may be absent if data is short)
        def _col(idx: int) -> str:
            return cols[idx].strip() if idx < len(cols) else ""

        open_val = parse_number(_col(1))
        high_val = parse_number(_col(2))
        low_val = parse_number(_col(3))
        vol_units_raw = parse_number(_col(4))
        vol_xof_raw = parse_number(_col(5))
        close_val = parse_number(_col(6))
        variation_raw = parse_pct(_col(7))

        results.append(
            {
                "symbol": symbol,
                "trading_date": date_iso,
                "open": open_val,
                "high": high_val,
                "low": low_val,
                "close": close_val,
                "volume_units": int(vol_units_raw) if vol_units_raw is not None else 0,
                "volume_xof": int(vol_xof_raw) if vol_xof_raw is not None else 0,
                "variation_pct": variation_raw,
            }
        )

    logger.info("parse_stocks: %d stocks parsed", len(results))
    return results


def parse_indices(text: str) -> Dict:
    """Parse tab-separated indices table.

    Expected column order:
        Nom | Ouverture | +Haut | +Bas | Dernier | Variation

    Returns a flat dict keyed by INDEX_NAME_MAP values:
        {
            "brvm_composite":      {"value": 421.55, "variation_pct": 0.81},
            "brvm_30":             {"value": 197.55, "variation_pct": 0.41},
            "capitalisation_fcfa": 16111022.0,   ← scalar, no variation
            ...
        }

    Silently skips unknown index names.
    """
    results: Dict = {}

    for line in text.strip().splitlines():
        cols = line.split("\t")
        if len(cols) < 2:
            continue

        raw_name = cols[0].strip()
        if raw_name == "Nom":  # header line
            continue

        mapped_key = _INDEX_MAP_UPPER.get(raw_name.upper())
        if mapped_key is None:
            logger.debug("Unknown index name %r — skipping", raw_name)
            continue

        # Dernier (last/close) is column 4; Variation is column 5
        dernier_str = cols[4].strip() if len(cols) > 4 else ""
        variation_str = cols[5].strip() if len(cols) > 5 else ""

        value = parse_number(dernier_str)
        if value is None:
            logger.debug("Index %r: could not parse value %r — skipping", raw_name, dernier_str)
            continue

        if mapped_key == "capitalisation_fcfa":
            # Market capitalisation stored as a scalar float
            results[mapped_key] = value
        else:
            variation = parse_pct(variation_str)
            results[mapped_key] = {"value": value, "variation_pct": variation}

    logger.info("parse_indices: %d indices parsed", len(results))
    return results


def parse_dividends(text: str) -> List[Dict]:
    """Parse tab-separated dividends table.

    Expected column order:
        Date détachement | Nom | Montant | Rendement

    Returns:
        [
            {
                "symbol": "SNTS",
                "montant_net": 1740.0,
                "date_detachement": "2026-05-22",   # None if "A préciser"
                "rendement_pct": 6.02
            },
            ...
        ]
    """
    results: List[Dict] = []

    for line in text.strip().splitlines():
        cols = line.split("\t")
        if len(cols) < 3:
            continue

        date_str = cols[0].strip()

        # Skip header lines: valid data starts with a date ("DD/MM/YYYY") or "A préciser"
        if date_str != "A préciser" and not _DATE_PATTERN.match(date_str):
            continue

        name = cols[1].strip() if len(cols) > 1 else ""
        if not name:
            continue

        # Resolve symbol
        try:
            symbol = resolve_symbol(name)
        except ValueError:
            logger.warning("Unknown company name %r in dividends — skipping", name)
            continue

        if symbol is None:
            logger.debug("Delisted company %r in dividends — skipping", name)
            continue

        montant_str = cols[2].strip() if len(cols) > 2 else ""
        rendement_str = cols[3].strip() if len(cols) > 3 else ""

        montant_net = parse_number(montant_str)
        date_detachement = parse_date_fr(date_str)
        rendement_pct = parse_pct(rendement_str)

        results.append(
            {
                "symbol": symbol,
                "montant_net": montant_net,
                "date_detachement": date_detachement,
                "rendement_pct": rendement_pct,
            }
        )

    logger.info("parse_dividends: %d dividends parsed", len(results))
    return results


# ---------------------------------------------------------------------------
# JSON builder
# ---------------------------------------------------------------------------

def build_json(
    stocks: List[Dict],
    indices: Dict,
    dividends: List[Dict],
    trading_date: date,
) -> Dict:
    """Merge stocks + indices + dividends into the canonical daily JSON structure.

    Dividend info is attached to the matching stock entry by symbol.

    Main indices (brvm_composite, brvm_30, brvm_prestige, brvm_principal,
    capitalisation_fcfa) are placed in ``indices`` root.
    All sector indices go in ``indices.sectoriels``.

    Output structure::

        {
            "metadata": {
                "trading_date": "2026-05-21",
                "generated_at": "2026-05-21T18:42:00Z",
                "total_stocks": 47,
                "source": "daily_import"
            },
            "indices": {
                "brvm_composite": {"value": 421.55, "variation_pct": 0.81},
                "capitalisation_fcfa": 16111022.0,
                "sectoriels": {
                    "brvm_agriculture": {"value": 341.63, "variation_pct": 3.07},
                    ...
                }
            },
            "stocks": [
                {
                    "symbol": "SNTS",
                    ...,
                    "dividend": {"montant_net": 1740.0, ...}  // or null
                }
            ]
        }
    """
    # Build dividend lookup by symbol (take last entry if duplicates)
    dividend_map: Dict[str, Dict] = {}
    for div in dividends:
        dividend_map[div["symbol"]] = {
            "montant_net": div.get("montant_net"),
            "date_detachement": div.get("date_detachement"),
            "rendement_pct": div.get("rendement_pct"),
        }

    # Attach dividends to stock entries
    stock_entries = []
    for stock in stocks:
        entry = dict(stock)
        entry["dividend"] = dividend_map.get(stock["symbol"])  # None if no dividend
        stock_entries.append(entry)

    # Split indices: main vs sectoriels
    indices_root: Dict = {}
    sectoriels: Dict = {}
    for key, val in indices.items():
        if key in _MAIN_INDICES:
            indices_root[key] = val
        else:
            sectoriels[key] = val

    if sectoriels:
        indices_root["sectoriels"] = sectoriels

    return {
        "metadata": {
            "trading_date": trading_date.isoformat(),
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_stocks": len(stock_entries),
            "source": "daily_import",
        },
        "indices": indices_root,
        "stocks": stock_entries,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Akwaba Invest — daily market data import (TSV to JSON)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--stocks",
        type=str,
        required=True,
        help="Path to tab-separated stocks data file",
    )
    parser.add_argument(
        "--indices",
        type=str,
        default=None,
        help="Path to tab-separated indices data file (optional)",
    )
    parser.add_argument(
        "--dividends",
        type=str,
        default=None,
        help="Path to tab-separated dividends data file (optional)",
    )
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="Trading date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (default: data/json/ relative to backend/)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging")
    args = parser.parse_args()

    _setup_logging(args.verbose)

    # Parse trading date
    try:
        trading_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        logger.error("Invalid --date value: %s (expected YYYY-MM-DD)", args.date)
        return 2

    # Read input files
    stocks_path = Path(args.stocks)
    if not stocks_path.exists():
        logger.error("Stocks file not found: %s", args.stocks)
        return 1

    stocks_text = stocks_path.read_text(encoding="utf-8")
    indices_text = (
        Path(args.indices).read_text(encoding="utf-8") if args.indices else None
    )
    dividends_text = (
        Path(args.dividends).read_text(encoding="utf-8") if args.dividends else None
    )

    # Parse
    stocks = parse_stocks(stocks_text, trading_date)
    indices = parse_indices(indices_text) if indices_text else {}
    dividends = parse_dividends(dividends_text) if dividends_text else []

    # Build JSON
    data = build_json(stocks, indices, dividends, trading_date)

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = _BACKEND_DIR / "data" / "json"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Write dated file + latest alias
    date_str = trading_date.strftime("%Y%m%d")
    json_path = output_dir / f"brvm_{date_str}.json"
    latest_path = output_dir / "latest.json"

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    with open(latest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    logger.info("JSON written to %s (and latest.json)", json_path)
    print(
        f"RESULT: success | date={trading_date} | stocks={len(stocks)} | output={json_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
