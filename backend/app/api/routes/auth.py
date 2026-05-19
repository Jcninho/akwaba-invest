import logging

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user, verify_firebase_token
from app.models import User
from app.schemas.user import UserMeResponse, UserRead
from app.services.user_service import get_active_subscription_end_date, upsert_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Register or fetch user from Firebase token",
)
def register(
    decoded_token: dict = Depends(verify_firebase_token),
    session: Session = Depends(get_session),
):
    """Upsert user in DB from Firebase token. Idempotent."""
    firebase_uid = decoded_token["uid"]
    email = decoded_token.get("email")
    return upsert_user(session, firebase_uid=firebase_uid, email=email)


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Get current authenticated user profile",
)
def get_me(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Return current user with subscription info."""
    end_date = get_active_subscription_end_date(session, user.id)
    return UserMeResponse(
        id=user.id,
        email=user.email,
        plan=user.plan,
        subscription_end_date=end_date,
    )
