import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.dependencies import require_premium

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
async def list_alerts(user: str = Depends(require_premium), session: Session = Depends(get_session)):
    # TODO: return all price/dividend alerts for the authenticated user
    raise NotImplementedError


@router.post("/")
async def create_alert(user: str = Depends(require_premium), session: Session = Depends(get_session)):
    # TODO: create alert with edge-trigger logic (last_trigger_state = False)
    raise NotImplementedError


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, user: str = Depends(require_premium), session: Session = Depends(get_session)):
    # TODO: delete alert by id, ensure ownership
    raise NotImplementedError
