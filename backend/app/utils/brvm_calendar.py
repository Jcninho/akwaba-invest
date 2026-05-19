"""
BRVM trading calendar utilities.

BRVM serves 8 UEMOA countries and follows a combined public holiday calendar
covering Côte d'Ivoire, Sénégal, Mali, Burkina Faso, Bénin, Togo, Niger,
and Guinée-Bissau. Update ALL_HOLIDAYS each year.
"""
import logging
from datetime import date, timedelta
from typing import Set

logger = logging.getLogger(__name__)


BRVM_HOLIDAYS_2025: Set[str] = {
    "2025-01-01",  # Jour de l'An
    "2025-04-21",  # Lundi de Pâques
    "2025-05-01",  # Fête du Travail
    "2025-05-29",  # Ascension
    "2025-06-09",  # Lundi de Pentecôte
    "2025-08-07",  # Fête Nationale CI
    "2025-08-15",  # Assomption
    "2025-11-01",  # Toussaint
    "2025-11-15",  # Fête Nationale CI
    "2025-12-25",  # Noël
}

BRVM_HOLIDAYS_2026: Set[str] = {
    "2026-01-01",  # Jour de l'An
    "2026-04-06",  # Lundi de Pâques
    "2026-05-01",  # Fête du Travail
    "2026-05-14",  # Ascension
    "2026-05-25",  # Lundi de Pentecôte
    "2026-08-07",  # Fête Nationale CI
    "2026-08-15",  # Assomption
    "2026-11-01",  # Toussaint
    "2026-11-15",  # Fête Nationale CI
    "2026-12-25",  # Noël
    "2026-03-30",  # Aïd el-Fitr (approx)
    "2026-06-06",  # Aïd el-Adha (approx)
}

ALL_HOLIDAYS: Set[str] = BRVM_HOLIDAYS_2025 | BRVM_HOLIDAYS_2026


def is_trading_day(target_date: date) -> bool:
    """Return True if the BRVM market is open on the given date."""
    if target_date.weekday() >= 5:
        return False
    if target_date.isoformat() in ALL_HOLIDAYS:
        return False
    return True


def get_last_trading_day(from_date: date) -> date:
    """Return the most recent trading day on or before from_date."""
    target = from_date
    for _ in range(10):
        if is_trading_day(target):
            return target
        target -= timedelta(days=1)
    logger.warning("Could not find a trading day in the 10 days before %s", from_date)
    return from_date


def get_next_trading_day(from_date: date) -> date:
    """Return the first trading day strictly after from_date."""
    target = from_date + timedelta(days=1)
    for _ in range(10):
        if is_trading_day(target):
            return target
        target += timedelta(days=1)
    logger.warning("Could not find a trading day in the 10 days after %s", from_date)
    return target
