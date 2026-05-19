import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.database import get_session
from app.firebase import verify_id_token
from app.models import User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def verify_firebase_token(token: str = Depends(oauth2_scheme)) -> dict:
    """Verify Firebase JWT and return decoded claims (firebase_uid, email)."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        decoded = verify_id_token(token)
        return decoded
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    decoded_token: dict = Depends(verify_firebase_token),
    session: Session = Depends(get_session),
) -> User:
    """Fetch the User row from DB using firebase_uid from token."""
    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing uid claim",
        )
    user = session.exec(
        select(User).where(User.firebase_uid == firebase_uid)
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database. Call /auth/register first.",
        )
    return user


def require_premium(user: User = Depends(get_current_user)) -> User:
    # TODO: check user.plan == 'premium', subscription.status == 'active',
    # subscription.end_date > now(). Raise 403 if not premium. (next task)
    raise NotImplementedError
