"""
BocRun service — manage idempotency journal for BOC parser runs.
"""
import logging
from datetime import date, datetime
from typing import Optional

from sqlmodel import Session, select

from app.models import BocRun

logger = logging.getLogger(__name__)


def is_boc_run_completed(session: Session, target_date: date) -> bool:
    """Return True if BOC for target_date has been successfully processed."""
    run = session.exec(
        select(BocRun).where(BocRun.run_date == target_date)
    ).first()
    if run is None:
        return False
    return run.status == "success"


def get_boc_run(session: Session, target_date: date) -> Optional[BocRun]:
    """Return the BocRun for target_date, or None if it doesn't exist."""
    return session.exec(
        select(BocRun).where(BocRun.run_date == target_date)
    ).first()


def start_boc_run(session: Session, target_date: date) -> BocRun:
    """
    Mark a BOC run as started. Idempotent: returns existing row if any,
    resetting it to a fresh "running" state.
    """
    existing = get_boc_run(session, target_date)
    if existing:
        existing.status = "running"
        existing.started_at = datetime.utcnow()
        existing.finished_at = None
        existing.error_message = None
        existing.stocks_parsed = 0
        session.add(existing)
        session.commit()
        session.refresh(existing)
        logger.info("BOC run reset for %s", target_date)
        return existing

    run = BocRun(
        run_date=target_date,
        status="running",
        stocks_parsed=0,
        started_at=datetime.utcnow(),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    logger.info("BOC run started for %s", target_date)
    return run


def mark_boc_run_success(
    session: Session,
    target_date: date,
    stocks_parsed: int,
) -> BocRun:
    """Mark a BOC run as successful."""
    run = get_boc_run(session, target_date)
    if run is None:
        raise ValueError(f"No BocRun found for {target_date}. Call start_boc_run first.")
    run.status = "success"
    run.stocks_parsed = stocks_parsed
    run.finished_at = datetime.utcnow()
    run.error_message = None
    session.add(run)
    session.commit()
    session.refresh(run)
    logger.info("BOC run succeeded for %s — %d stocks parsed", target_date, stocks_parsed)
    return run


def mark_boc_run_failed(
    session: Session,
    target_date: date,
    error_message: str,
) -> BocRun:
    """Mark a BOC run as failed with an error message."""
    run = get_boc_run(session, target_date)
    if run is None:
        raise ValueError(f"No BocRun found for {target_date}. Call start_boc_run first.")
    run.status = "failed"
    run.finished_at = datetime.utcnow()
    run.error_message = error_message[:1000]  # truncate long stack traces
    session.add(run)
    session.commit()
    session.refresh(run)
    logger.warning("BOC run failed for %s: %s", target_date, error_message[:200])
    return run
