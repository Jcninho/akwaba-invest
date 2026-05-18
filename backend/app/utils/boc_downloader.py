import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


def download_boc(trading_date: date, output_dir: Path) -> Path:
    # TODO: fetch BOC PDF from BRVM website for the given date; save to output_dir
    # Return the path to the downloaded file
    raise NotImplementedError


def get_latest_boc_url(trading_date: date) -> str:
    # TODO: build BRVM BOC URL for the given trading date
    raise NotImplementedError


def is_brvm_trading_day(trading_date: date) -> bool:
    # TODO: return True if BRVM is open on trading_date (exclude weekends + holidays)
    raise NotImplementedError
