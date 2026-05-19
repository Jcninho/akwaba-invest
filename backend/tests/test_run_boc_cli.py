"""Integration tests for scripts/run_boc.py CLI."""
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from app.models import BocRun, DailyPrice, Stock


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run_boc.py"


@pytest.fixture
def in_memory_engine(monkeypatch):
    """Replace the production engine with in-memory SQLite for the run_boc module."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    # Patch the engine in the database module — run_boc accesses it as _database.engine
    monkeypatch.setattr("app.database.engine", engine)
    return engine


def _mock_stocks():
    return [
        {
            "symbol": "SNTS", "name": "SONATEL SN", "sector": "TEL",
            "sector_name": "Télécommunications",
            "price": 28800.0, "open": 28850.0, "change_pct": -0.35,
            "volume": 14844, "value": 428648545,
            "dividend": 1655.0, "dividend_date": "2025-05-22",
            "per": 6.96, "boc_date": "2026-05-18",
        },
        {
            "symbol": "NTLC", "name": "NESTLE CI", "sector": "CB",
            "sector_name": "Consommation de Base",
            "price": 11950.0, "open": 11750.0, "change_pct": 1.70,
            "volume": 686, "value": 8064220,
            "dividend": 721.6, "dividend_date": "2025-08-18",
            "per": 14.31, "boc_date": "2026-05-18",
        },
    ]


# ── Module import tests ───────────────────────────────────────────────────────

def test_script_imports_without_error():
    """Sanity check: script imports cleanly."""
    sys.path.insert(0, str(SCRIPT_PATH.parent.parent))
    import scripts.run_boc as run_boc_mod
    assert hasattr(run_boc_mod, "main")
    assert hasattr(run_boc_mod, "_resolve_target_date")


def test_resolve_target_date_today():
    from scripts.run_boc import _resolve_target_date
    import logging
    logger = logging.getLogger("test")
    assert _resolve_target_date("today", logger) == date.today()


def test_resolve_target_date_explicit():
    from scripts.run_boc import _resolve_target_date
    import logging
    logger = logging.getLogger("test")
    assert _resolve_target_date("2026-05-18", logger) == date(2026, 5, 18)


def test_resolve_target_date_invalid_exits():
    from scripts.run_boc import _resolve_target_date
    import logging
    logger = logging.getLogger("test")
    with pytest.raises(SystemExit) as exc:
        _resolve_target_date("not-a-date", logger)
    assert exc.value.code == 2


# ── End-to-end main() with mocks ─────────────────────────────────────────────

def test_main_success_with_mocked_pdf(in_memory_engine, tmp_path, monkeypatch, capsys):
    """Full happy path: provide --file, mock parser, check DB write + exit code."""
    fake_pdf = tmp_path / "boc_20260518_2.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)

    monkeypatch.setattr(sys, "argv", [
        "run_boc.py",
        "--date", "2026-05-18",
        "--file", str(fake_pdf),
    ])

    with patch("app.services.stock_service.parse_stocks_from_pdf", return_value=_mock_stocks()):
        from scripts.run_boc import main
        exit_code = main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "RESULT: success" in captured.out
    assert "stocks=2" in captured.out

    with Session(in_memory_engine) as s:
        stocks = s.exec(select(Stock)).all()
        prices = s.exec(select(DailyPrice)).all()
        runs = s.exec(select(BocRun)).all()
        assert len(stocks) == 2
        assert len(prices) == 2
        assert len(runs) == 1
        assert runs[0].status == "success"


def test_main_missing_file_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "run_boc.py",
        "--date", "2026-05-18",
        "--file", "/nonexistent/path.pdf",
    ])
    from scripts.run_boc import main
    exit_code = main()
    assert exit_code == 1


def test_main_no_data_parsed_exits_1(in_memory_engine, tmp_path, monkeypatch, capsys):
    fake_pdf = tmp_path / "boc_20260518_2.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)

    monkeypatch.setattr(sys, "argv", [
        "run_boc.py",
        "--date", "2026-05-18",
        "--file", str(fake_pdf),
    ])

    with patch("app.services.stock_service.parse_stocks_from_pdf", return_value=[]):
        from scripts.run_boc import main
        exit_code = main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "RESULT: no_data" in captured.out


def test_main_parser_crash_exits_1(in_memory_engine, tmp_path, monkeypatch, capsys):
    fake_pdf = tmp_path / "boc_20260518_2.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)

    monkeypatch.setattr(sys, "argv", [
        "run_boc.py",
        "--date", "2026-05-18",
        "--file", str(fake_pdf),
    ])

    with patch(
        "app.services.stock_service.parse_stocks_from_pdf",
        side_effect=Exception("Corrupted PDF"),
    ):
        from scripts.run_boc import main
        exit_code = main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "RESULT: parse_failed" in captured.out


def test_main_force_reprocesses(in_memory_engine, tmp_path, monkeypatch, capsys):
    fake_pdf = tmp_path / "boc_20260518_2.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\n" + b"x" * 2000)

    monkeypatch.setattr(sys, "argv", [
        "run_boc.py",
        "--date", "2026-05-18",
        "--file", str(fake_pdf),
        "--force",
    ])

    with patch("app.services.stock_service.parse_stocks_from_pdf", return_value=_mock_stocks()):
        from scripts.run_boc import main
        # First run
        assert main() == 0
        # Second run with --force should also succeed
        assert main() == 0

    captured = capsys.readouterr()
    assert captured.out.count("RESULT: success") == 2
