"""
BRVM BOC PDF parser for Akwaba Invest.

Extracts stock data from the Bulletin Officiel de la Cote (BOC).

Column layout in stock rows (16 columns, pdfplumber split):
  [0]  Sector code   "CB"
  [1]  Symbol        "NTLC"
  [2]  Name          "NESTLE CI"
  [3]  Empty         ""   <- compartiment marker, always blank in data rows
  [4]  Prev close    "11 700"
  [5]  Open          "11 400"
  [6]  Close/Price   "11 600"
  [7]  Change %      "-0,85 %"
  [8]  Volume        "437"
  [9]  Value (FCFA)  "5 027 150"
  [10] Ref price     "11 600"
  [11] YTD change %  "8,92 %"
  [12] Dividend      "721,6"
  [13] Dividend date "18-août-25"
  [14] Net yield %   "6,22 %"
  [15] PER           "13,89"
"""
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import pdfplumber

logger = logging.getLogger(__name__)

SECTOR_CODES: Dict[str, str] = {
    "TEL": "Télécommunications",
    "FIN": "Services Financiers",
    "CB":  "Consommation de Base",
    "CD":  "Consommation Discrétionnaire",
    "IND": "Industriels",
    "ENE": "Énergie",
    "SPU": "Services Publics",
}

STOCK_PAGES = [2, 3]
INDEX_PAGE  = 0

_SKIP_SYMBOLS = {"Symbole", "TOTAL", "Code", ""}


def parse_price(value: str) -> Optional[float]:
    """Parse a French-formatted price string to float."""
    if not value:
        return None
    cleaned = value.strip()
    if cleaned in ("", "NC", "SP", "-", "ND", "Marché"):
        return None
    cleaned = cleaned.replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_pct(value: str) -> Optional[float]:
    """Parse a French-formatted percentage string to float."""
    if not value:
        return None
    cleaned = value.strip()
    if cleaned in ("", "NC", "-", "ND"):
        return None
    cleaned = (
        cleaned.replace("%", "").replace(" ", "").replace("\xa0", "")
               .replace("+", "").replace(",", ".")
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_int(value: str) -> Optional[int]:
    """Parse a French-formatted integer string."""
    if not value:
        return None
    cleaned = value.strip()
    if cleaned in ("", "NC", "-", "ND"):
        return None
    cleaned = cleaned.replace(" ", "").replace("\xa0", "")
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def parse_date(value: str) -> Optional[str]:
    """Parse a French date string to ISO format (YYYY-MM-DD)."""
    if not value:
        return None
    cleaned = value.strip()
    if cleaned in ("", "NC", "-", "ND"):
        return None

    _MONTHS: Dict[str, str] = {
        "janv": "01", "jan":  "01",
        "févr": "02", "fév":  "02", "fevr": "02",
        "mars": "03",
        "avr":  "04",
        "mai":  "05",
        "juin": "06",
        "juil": "07", "jul":  "07",
        "août": "08", "aout": "08",
        "sept": "09", "sep":  "09",
        "oct":  "10",
        "nov":  "11",
        "déc":  "12", "dec":  "12",
    }

    parts = cleaned.replace(".", "").split("-")
    if len(parts) != 3:
        return None

    day, month_raw, year = parts
    month = _MONTHS.get(month_raw.lower().rstrip("."))
    if not month:
        return None

    full_year = f"20{year}" if len(year) == 2 else year
    try:
        return f"{full_year}-{month}-{day.zfill(2)}"
    except Exception:
        return None


def validate_stock(stock: Dict[str, Any]) -> bool:
    """Validate parsed stock data before saving."""
    if not stock.get("symbol"):
        return False
    price = stock.get("price")
    if price is None or price <= 0:
        return False
    change_pct = stock.get("change_pct")
    if change_pct is not None and abs(change_pct) > 100:
        return False
    return True


def parse_stock_row(row: List[Optional[str]], boc_date: date) -> Optional[Dict[str, Any]]:
    """Parse a single PDF table row into a stock dict."""
    cells = [str(c).strip() if c is not None else "" for c in row]

    if len(cells) < 14:
        return None

    symbol = cells[1]

    if not symbol or symbol in _SKIP_SYMBOLS or len(symbol) > 12:
        return None
    if symbol.upper().startswith("COMPARTIMENT"):
        return None

    def _get(idx: int) -> str:
        return cells[idx] if idx < len(cells) else ""

    stock: Dict[str, Any] = {
        "symbol":        symbol,
        "name":          cells[2].replace("\n", " ").strip(),
        "sector":        cells[0],
        "sector_name":   SECTOR_CODES.get(cells[0], ""),
        "prev_close":    parse_price(_get(4)),
        "open":          parse_price(_get(5)),
        "price":         parse_price(_get(6)),
        "change_pct":    parse_pct(_get(7)),
        "volume":        parse_int(_get(8)),
        "value":         parse_int(_get(9)),
        "ref_price":     parse_price(_get(10)),
        "yearly_change": parse_pct(_get(11)),
        "dividend":      parse_price(_get(12)),
        "dividend_date": parse_date(_get(13)),
        "dividend_yield":parse_pct(_get(14)),
        "per":           parse_price(_get(15)),
        "boc_date":      boc_date.isoformat(),
    }

    try:
        return stock if validate_stock(stock) else None
    except Exception as exc:
        logger.warning("Error validating row %s: %s", row, exc)
        return None


def parse_stocks_from_pdf(pdf_path: Path, boc_date: date) -> List[Dict[str, Any]]:
    """Extract all stock data from a BOC PDF."""
    stocks: List[Dict[str, Any]] = []

    logger.info("Parsing stocks from: %s", pdf_path)

    with pdfplumber.open(str(pdf_path)) as pdf:
        total_pages = len(pdf.pages)
        logger.info("PDF has %d pages", total_pages)

        for page_idx in STOCK_PAGES:
            if page_idx >= total_pages:
                logger.warning("Page %d not found in PDF (only %d pages)", page_idx + 1, total_pages)
                continue

            page = pdf.pages[page_idx]
            tables = page.extract_tables()

            if not tables:
                logger.warning("No tables found on page %d", page_idx + 1)
                continue

            for table in tables:
                for row in table:
                    if not row:
                        continue
                    stock = parse_stock_row(row, boc_date)
                    if stock:
                        stocks.append(stock)

    seen: set = set()
    unique: List[Dict[str, Any]] = []
    for s in stocks:
        if s["symbol"] not in seen:
            seen.add(s["symbol"])
            unique.append(s)

    logger.info("Total stocks parsed (unique): %d", len(unique))
    return unique


def parse_indices_from_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Extract market indices from BOC page 1."""
    indices: Dict[str, Any] = {
        "brvm_composite":        None,
        "brvm_composite_change": None,
        "brvm_composite_ytd":    None,
        "brvm_30":               None,
        "brvm_30_change":        None,
        "brvm_prestige":         None,
        "brvm_prestige_change":  None,
    }

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            if not pdf.pages:
                return indices

            text = pdf.pages[INDEX_PAGE].extract_text() or ""

            for pattern, key in [
                (r"BRVM COMPOSITE\s+([\d\s,\.]+)", "brvm_composite"),
                (r"BRVM 30\s+([\d\s,\.]+)",        "brvm_30"),
                (r"BRVM PRESTIGE\s+([\d\s,\.]+)",  "brvm_prestige"),
            ]:
                m = re.search(pattern, text)
                if m:
                    indices[key] = parse_price(m.group(1))

            day_changes = re.findall(r"Variation Jour\s+([\+\-]?[\d\s,\.]+\s*%)", text)
            change_keys = ["brvm_composite_change", "brvm_30_change", "brvm_prestige_change"]
            for key, raw in zip(change_keys, day_changes):
                indices[key] = parse_pct(raw)

    except Exception as exc:
        logger.error("Error parsing indices from %s: %s", pdf_path, exc)

    return indices
