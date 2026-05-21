"""
Upload UI route — serves the mobile-friendly data upload page.

The page itself is a standalone HTML file with embedded CSS and JS.
No authentication required to load the page; the admin key is submitted
via the form and checked by the /admin/upload-daily API endpoint.
"""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "static"


@router.get("/upload", include_in_schema=False)
async def upload_page() -> FileResponse:
    """Serve the daily market data upload interface."""
    return FileResponse(STATIC_DIR / "upload.html")
