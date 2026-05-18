"""CLI script to manually trigger BOC parsing for a given date.

Usage:
    python scripts/run_boc.py --date today
    python scripts/run_boc.py --date 2026-05-15
"""
import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BOC parser for a trading date")
    parser.add_argument(
        "--date",
        required=True,
        help="Trading date: 'today' or YYYY-MM-DD",
    )
    return parser.parse_args()


def resolve_date(raw: str) -> date:
    if raw == "today":
        return date.today()
    return datetime.strptime(raw, "%Y-%m-%d").date()


def main() -> None:
    args = parse_args()
    trading_date = resolve_date(args.date)
    logger.info("Starting BOC run for %s", trading_date)
    # TODO: check boc_runs idempotence, download PDF, parse, persist daily_prices
    raise NotImplementedError("BOC pipeline not yet implemented")


if __name__ == "__main__":
    main()
