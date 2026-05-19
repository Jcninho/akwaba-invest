"""Unit tests for boc_downloader pure helpers."""
from datetime import date
from pathlib import Path

from app.utils.boc_downloader import (
    _is_valid_pdf,
    _local_path,
    extract_bulletin_number,
    BOC_LOCAL_DIR,
    BULLETIN_NUMBERS,
)


def test_is_valid_pdf_too_short():
    assert _is_valid_pdf(b"%PDF-tiny") is False


def test_is_valid_pdf_wrong_magic():
    assert _is_valid_pdf(b"NOPDF" + b"x" * 2000) is False


def test_is_valid_pdf_valid():
    content = b"%PDF-1.4" + b"x" * 2000
    assert _is_valid_pdf(content) is True


def test_local_path_format():
    p = _local_path(date(2026, 5, 18), 2)
    assert p.name == "boc_20260518_2.pdf"
    assert p.parent == BOC_LOCAL_DIR


def test_extract_bulletin_number_simple():
    p = Path("/tmp/akwaba_boc/boc_20260518_2.pdf")
    assert extract_bulletin_number(p) == 2


def test_extract_bulletin_number_different_number():
    p = Path("/tmp/akwaba_boc/boc_20260513_5.pdf")
    assert extract_bulletin_number(p) == 5


def test_extract_bulletin_number_invalid():
    p = Path("/tmp/random.pdf")
    assert extract_bulletin_number(p) is None


def test_bulletin_numbers_descending():
    assert BULLETIN_NUMBERS == [5, 4, 3, 2, 1]
