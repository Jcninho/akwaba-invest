import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Public holidays observed by BRVM (static list, updated annually)
BRVM_HOLIDAYS: frozenset[date] = frozenset()


def is_trading_day(d: date) -> bool:
    # TODO: return False for weekends and BRVM_HOLIDAYS
    raise NotImplementedError


def previous_trading_day(d: date) -> date:
    # TODO: walk backwards from d-1 until is_trading_day returns True
    raise NotImplementedError


def next_trading_day(d: date) -> date:
    # TODO: walk forward from d+1 until is_trading_day returns True
    raise NotImplementedError
