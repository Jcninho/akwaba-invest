"""
Alert management routes.

All endpoints require authentication (get_current_user).
Business logic is delegated to alert_service.

Routes:
    GET    /alerts/                     -- list user's alerts
    POST   /alerts/                     -- create a new alert
    DELETE /alerts/{alert_id}           -- delete an alert
    PATCH  /alerts/{alert_id}/toggle    -- activate / deactivate
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models import User
from app.schemas.alert import AlertCreate, AlertRead, AlertToggle
from app.services.alert_service import (
    build_alert_read,
    create_alert,
    delete_alert,
    get_user_alerts,
    toggle_alert,
)
from app.utils.exceptions import AlertNotFoundError, StockNotFoundError

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)


def _alert_read(session: Session, alert) -> AlertRead:
    """Convert an Alert ORM object to an AlertRead schema via enriched dict."""
    return AlertRead.model_validate(build_alert_read(session, alert))


@router.get("/", response_model=List[AlertRead])
def list_alerts(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> List[AlertRead]:
    """Return all alerts for the authenticated user, newest first."""
    alerts = get_user_alerts(session, current_user.id)
    return [_alert_read(session, a) for a in alerts]


@router.post("/", response_model=AlertRead, status_code=201)
def create_alert_route(
    body: AlertCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AlertRead:
    """
    Create a new price or dividend alert.

    - price_above / price_below: threshold (FCFA) is required and must be > 0.
    - dividend: threshold is ignored.
    """
    try:
        alert = create_alert(
            session,
            user_id=current_user.id,
            symbol=body.symbol,
            alert_type=body.alert_type,
            threshold=body.threshold,
        )
    except StockNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    return _alert_read(session, alert)


@router.delete("/{alert_id}", status_code=204)
def delete_alert_route(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    """Delete an alert. Returns 404 if not found or belongs to another user."""
    try:
        delete_alert(session, alert_id=alert_id, user_id=current_user.id)
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.patch("/{alert_id}/toggle", response_model=AlertRead)
def toggle_alert_route(
    alert_id: int,
    body: AlertToggle,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AlertRead:
    """
    Activate or deactivate an alert.

    When reactivating (is_active=True), last_trigger_state resets to False
    so the alert can fire again immediately if the condition is met.
    """
    try:
        alert = toggle_alert(
            session,
            alert_id=alert_id,
            user_id=current_user.id,
            is_active=body.is_active,
        )
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    return _alert_read(session, alert)
