"""
BRVM BOC PDF downloader.

BOC = Bulletin Officiel de la Cote
Published daily after market close (~16h00–17h00 Abidjan time).

Filename pattern: boc_YYYYMMDD_N.pdf where N is the bulletin number (1-5).
URL pattern: https://www.brvm.org/sites/default/files/boc_YYYYMMDD_N.pdf

We try bulletin numbers in descending order (5 → 1) because the highest
number is the most complete bulletin of the day.
"""
import logging
import re
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import requests
import urllib3

from app.utils.brvm_calendar import is_trading_day
from app.utils.exceptions import BocDownloadError

# brvm.org has a misconfigured SSL certificate — suppress warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

BOC_BASE_URL      = "https://www.brvm.org/sites/default/files"
BOC_LOCAL_DIR     = Path(tempfile.gettempdir()) / "akwaba_boc"
BULLETIN_NUMBERS  = list(range(5, 0, -1))  # try 5 → 1 (highest = most complete)
MAX_DAYS_BACK     = 5
REQUEST_TIMEOUT   = 20

_HEADERS    = {"User-Agent": "Mozilla/5.0 (compatible; AkwabaInvest/1.0)"}
_SSL_VERIFY = False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_valid_pdf(content: bytes) -> bool:
    """Return True if the bytes content is a non-trivial PDF."""
    return len(content) > 1000 and content[:4] == b"%PDF"


def _local_path(target_date: date, num: int) -> Path:
    """Return the local cache path for a given date + bulletin number."""
    BOC_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    return BOC_LOCAL_DIR / f"boc_{target_date:%Y%m%d}_{num}.pdf"


def extract_bulletin_number(pdf_path: Path) -> Optional[int]:
    """Extract the bulletin number N from a filename like boc_YYYYMMDD_N.pdf."""
    match = re.search(r"boc_\d{8}_(\d+)", pdf_path.name)
    if match:
        return int(match.group(1))
    return None


# ── Core download ─────────────────────────────────────────────────────────────

def try_download_boc(target_date: date) -> Optional[Path]:
    """
    Try to download the BOC PDF for target_date.

    Tries bulletin numbers 5 → 1 and returns the first valid PDF found.
    Returns the cached file immediately if already downloaded.

    Args:
        target_date: Date to fetch the BOC for.

    Returns:
        Path to the local PDF file, or None if not available.
    """
    date_str = target_date.strftime("%Y%m%d")

    for num in BULLETIN_NUMBERS:
        local_path = _local_path(target_date, num)

        if local_path.exists():
            logger.info("BOC cached: %s", local_path.name)
            return local_path

        url = f"{BOC_BASE_URL}/boc_{date_str}_{num}.pdf"
        logger.debug("Trying: %s", url)

        try:
            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers=_HEADERS,
                verify=_SSL_VERIFY,
                stream=True,
            )

            if response.status_code != 200:
                continue

            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower():
                continue

            content = response.content
            if not _is_valid_pdf(content):
                continue

            tmp_path = local_path.with_suffix(".tmp")
            tmp_path.write_bytes(content)
            tmp_path.replace(local_path)

            logger.info(
                "BOC downloaded: boc_%s_%d.pdf (%d KB)",
                date_str, num, len(content) // 1024,
            )
            return local_path

        except requests.RequestException as exc:
            logger.warning("Request failed for %s: %s", url, exc)

    logger.info("BOC not available yet for %s", target_date)
    return None


def get_latest_boc() -> Path:
    """
    Return the path to the most recent available BOC PDF.

    Scans dates in descending order, skipping weekends and holidays,
    up to MAX_DAYS_BACK trading days back.

    Returns:
        Path to the most recent BOC PDF.

    Raises:
        BocDownloadError: If no BOC is found within MAX_DAYS_BACK trading days.
    """
    today        = date.today()
    current      = today
    days_checked = 0

    logger.info("Searching for latest BOC (up to %d trading days back)…", MAX_DAYS_BACK)

    while days_checked <= MAX_DAYS_BACK:
        # Cache check first — avoid network if we already have it
        for num in BULLETIN_NUMBERS:
            cached = _local_path(current, num)
            if cached.exists():
                logger.info("Latest BOC found in cache: %s", cached.name)
                return cached

        if is_trading_day(current):
            pdf_path = try_download_boc(current)
            if pdf_path:
                logger.info("Latest BOC found: %s", pdf_path.name)
                return pdf_path
            days_checked += 1
        else:
            logger.debug("%s is not a trading day — skipping", current)

        current -= timedelta(days=1)

    raise BocDownloadError(today)
