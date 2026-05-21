"""
Admin routes — protected by X-Admin-Key header.

All endpoints here require a valid ADMIN_API_KEY passed as the
``X-Admin-Key`` request header.  Key comparison is constant-time
(via ``secrets.compare_digest``) to prevent timing attacks.
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from app.database import get_session
from app.dependencies import verify_admin_key
from app.services.boc_run_service import get_boc_run
from app.services.market_import_service import process_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/upload-daily")
async def upload_daily_data(
    trading_date: str = Form(..., description="Trading date in YYYY-MM-DD format"),
    stocks_file: UploadFile = File(..., description="Tab-separated stocks data (required)"),
    indices_file: Optional[UploadFile] = File(None, description="Tab-separated indices data"),
    dividends_file: Optional[UploadFile] = File(None, description="Tab-separated dividends data"),
    force: bool = Form(default=False, description="Re-process if already done for this date"),
    admin_key: str = Depends(verify_admin_key),
    session: Session = Depends(get_session),
) -> dict:
    """Upload daily market data files and trigger the full import pipeline.

    Accepts up to three TSV files (stocks required, indices and dividends
    optional).  Runs synchronously — files are small (< 50 KB each).

    Returns a summary dict on success::

        {
            "status": "success",
            "trading_date": "2026-05-21",
            "stocks_parsed": 47,
            "stocks_written": 47,
            "indices_parsed": 5,
            "dividends_parsed": 23,
            "json_path": "..."
        }
    """
    # Validate date
    try:
        target_date = date.fromisoformat(trading_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trading_date format: {trading_date!r} — expected YYYY-MM-DD",
        )

    # Read uploaded file contents
    stocks_text = (await stocks_file.read()).decode("utf-8")

    indices_text: Optional[str] = None
    if indices_file is not None:
        indices_text = (await indices_file.read()).decode("utf-8")

    dividends_text: Optional[str] = None
    if dividends_file is not None:
        dividends_text = (await dividends_file.read()).decode("utf-8")

    logger.info(
        "upload_daily_data received: date=%s stocks_len=%d indices=%s dividends=%s force=%s",
        target_date,
        len(stocks_text),
        "yes" if indices_text else "no",
        "yes" if dividends_text else "no",
        force,
    )

    try:
        result = process_upload(
            stocks_text=stocks_text,
            indices_text=indices_text,
            dividends_text=dividends_text,
            trading_date=target_date,
            session=session,
            force=force,
        )
    except Exception as exc:
        logger.exception("process_upload failed for date=%s", target_date)
        raise HTTPException(status_code=500, detail=str(exc))

    return result


@router.get("/import-status/{trading_date}")
async def get_import_status(
    trading_date: str,
    admin_key: str = Depends(verify_admin_key),
    session: Session = Depends(get_session),
) -> dict:
    """Return the boc_run status for a given trading date.

    Returns 404 if no import has ever been attempted for that date.
    """
    try:
        target_date = date.fromisoformat(trading_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {trading_date!r} — expected YYYY-MM-DD",
        )

    run = get_boc_run(session, target_date)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"No import found for trading date {trading_date}",
        )

    return {
        "trading_date": str(target_date),
        "status": run.status,
        "stocks_parsed": run.stocks_parsed,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error_message": run.error_message,
    }
