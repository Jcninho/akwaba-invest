"""
Akwaba Invest — BOC ingestion CLI.

Manually trigger BOC PDF download + parse + PostgreSQL persistence.
Designed to be safe to call multiple times (idempotent).

Examples:
    python scripts/run_boc.py
    python scripts/run_boc.py --date 2026-05-18
    python scripts/run_boc.py --date latest
    python scripts/run_boc.py --file /path/to/boc.pdf --date 2026-05-18
    python scripts/run_boc.py --date 2026-05-18 --force
"""
import argparse
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure backend/ is in PYTHONPATH so "from app.xxx" imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.database as _database  # access engine at call time for monkeypatching
from sqlmodel import Session

from app.services.stock_service import process_boc
from app.utils.boc_downloader import extract_bulletin_number, get_latest_boc, try_download_boc
from app.utils.brvm_calendar import is_trading_day
from app.utils.exceptions import BocDownloadError, BocParseError, NoDataError


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Akwaba Invest — BOC ingestion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date",
        type=str,
        default="today",
        help="Target date (YYYY-MM-DD), 'today' (default), or 'latest'",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Use a local PDF file instead of downloading from brvm.org",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process even if already completed for that date",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return parser.parse_args()


def _resolve_target_date(date_arg: str, logger: logging.Logger) -> date:
    """Resolve --date argument to a concrete date."""
    if date_arg == "today":
        return date.today()
    if date_arg == "latest":
        # Caller will use get_latest_boc which handles trading day logic
        return date.today()
    try:
        return datetime.strptime(date_arg, "%Y-%m-%d").date()
    except ValueError:
        logger.error(
            "Invalid --date value: %s (expected YYYY-MM-DD, 'today', or 'latest')",
            date_arg,
        )
        sys.exit(2)


def _resolve_pdf_path(
    args: argparse.Namespace, target_date: date, logger: logging.Logger
) -> Path:
    """Determine which PDF to use: --file, --date latest, or download for target_date."""
    if args.file:
        pdf_path = Path(args.file)
        if not pdf_path.exists():
            raise FileNotFoundError(f"File not found: {args.file}")
        logger.info("Using local file: %s", pdf_path)
        return pdf_path

    if args.date == "latest":
        logger.info("Fetching latest available BOC…")
        return get_latest_boc()

    if not is_trading_day(target_date):
        logger.warning(
            "%s is not a trading day — no BOC expected. Use --force if you really mean it.",
            target_date,
        )

    logger.info("Downloading BOC for %s…", target_date)
    pdf_path = try_download_boc(target_date)
    if pdf_path is None:
        raise BocDownloadError(target_date)
    return pdf_path


def main() -> int:
    args = _parse_args()
    _setup_logging(args.verbose)
    logger = logging.getLogger("run_boc")

    target_date = _resolve_target_date(args.date, logger)
    logger.info(
        "=== BOC ingestion starting | target_date=%s | force=%s ===",
        target_date, args.force,
    )

    try:
        pdf_path = _resolve_pdf_path(args, target_date, logger)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        return 1
    except BocDownloadError as exc:
        logger.error("Download failed: %s", exc.message)
        print(f"RESULT: failed_download | date={target_date} | stocks=0")
        return 1

    bulletin_num = extract_bulletin_number(pdf_path)
    if bulletin_num is not None:
        logger.info("Using bulletin number: %d", bulletin_num)

    # If --date latest was used, derive the actual date from the filename
    if args.date == "latest":
        match = re.search(r"boc_(\d{8})_\d+", pdf_path.name)
        if match:
            target_date = datetime.strptime(match.group(1), "%Y%m%d").date()
            logger.info("Latest BOC resolved to date: %s", target_date)

    try:
        with Session(_database.engine) as session:
            count = process_boc(session, pdf_path, target_date, force=args.force)
    except NoDataError as exc:
        logger.error("No data parsed: %s", exc.message)
        print(f"RESULT: no_data | date={target_date} | stocks=0")
        return 1
    except BocParseError as exc:
        logger.error("Parser failed: %s", exc.message)
        print(f"RESULT: parse_failed | date={target_date} | stocks=0")
        return 1
    except Exception:
        logger.exception("Unexpected error during ingestion")
        print(f"RESULT: error | date={target_date} | stocks=0")
        return 1

    logger.info("=== BOC ingestion complete | stocks=%d ===", count)
    print(f"RESULT: success | date={target_date} | stocks={count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
