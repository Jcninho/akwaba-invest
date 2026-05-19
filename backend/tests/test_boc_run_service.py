"""Unit tests for boc_run_service with in-memory SQLite."""
import pytest
from datetime import date
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from app.models import BocRun
from app.services.boc_run_service import (
    is_boc_run_completed,
    get_boc_run,
    start_boc_run,
    mark_boc_run_success,
    mark_boc_run_failed,
)


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


# ── is_boc_run_completed ──────────────────────────────────────────────────────

def test_is_boc_run_completed_no_record(session):
    assert is_boc_run_completed(session, date(2026, 5, 18)) is False


def test_is_boc_run_completed_success(session):
    start_boc_run(session, date(2026, 5, 18))
    mark_boc_run_success(session, date(2026, 5, 18), stocks_parsed=47)
    assert is_boc_run_completed(session, date(2026, 5, 18)) is True


def test_is_boc_run_completed_failed_returns_false(session):
    start_boc_run(session, date(2026, 5, 18))
    mark_boc_run_failed(session, date(2026, 5, 18), error_message="parse error")
    assert is_boc_run_completed(session, date(2026, 5, 18)) is False


def test_is_boc_run_completed_running_returns_false(session):
    start_boc_run(session, date(2026, 5, 18))
    assert is_boc_run_completed(session, date(2026, 5, 18)) is False


# ── start_boc_run ─────────────────────────────────────────────────────────────

def test_start_boc_run_creates_new(session):
    run = start_boc_run(session, date(2026, 5, 18))
    assert run.id is not None
    assert run.status == "running"
    assert run.stocks_parsed == 0
    assert run.started_at is not None
    assert run.finished_at is None


def test_start_boc_run_resets_existing(session):
    run1 = start_boc_run(session, date(2026, 5, 18))
    mark_boc_run_failed(session, date(2026, 5, 18), "previous failure")
    run2 = start_boc_run(session, date(2026, 5, 18))
    assert run1.id == run2.id  # same row reused
    assert run2.status == "running"
    assert run2.error_message is None
    assert run2.finished_at is None


# ── mark_boc_run_success ──────────────────────────────────────────────────────

def test_mark_boc_run_success(session):
    start_boc_run(session, date(2026, 5, 18))
    run = mark_boc_run_success(session, date(2026, 5, 18), stocks_parsed=47)
    assert run.status == "success"
    assert run.stocks_parsed == 47
    assert run.finished_at is not None


def test_mark_boc_run_success_without_start_raises(session):
    with pytest.raises(ValueError, match="No BocRun found"):
        mark_boc_run_success(session, date(2026, 5, 18), stocks_parsed=47)


# ── mark_boc_run_failed ───────────────────────────────────────────────────────

def test_mark_boc_run_failed(session):
    start_boc_run(session, date(2026, 5, 18))
    run = mark_boc_run_failed(session, date(2026, 5, 18), error_message="parse error")
    assert run.status == "failed"
    assert run.error_message == "parse error"
    assert run.finished_at is not None


def test_mark_boc_run_failed_truncates_long_message(session):
    start_boc_run(session, date(2026, 5, 18))
    long_msg = "x" * 5000
    run = mark_boc_run_failed(session, date(2026, 5, 18), error_message=long_msg)
    assert len(run.error_message) == 1000


def test_mark_boc_run_failed_without_start_raises(session):
    with pytest.raises(ValueError, match="No BocRun found"):
        mark_boc_run_failed(session, date(2026, 5, 18), "error")


# ── get_boc_run ───────────────────────────────────────────────────────────────

def test_get_boc_run_existing(session):
    start_boc_run(session, date(2026, 5, 18))
    run = get_boc_run(session, date(2026, 5, 18))
    assert run is not None
    assert run.run_date == date(2026, 5, 18)


def test_get_boc_run_not_found(session):
    assert get_boc_run(session, date(2026, 5, 18)) is None
