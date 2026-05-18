import logging

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def verify_firebase_token(token: str = Depends(oauth2_scheme)) -> str:
    # TODO: verify JWT with firebase-admin, raise 401 if invalid
    raise NotImplementedError


async def require_premium(user: str = Depends(verify_firebase_token)) -> str:
    # TODO: check user.plan == 'premium', subscription.status == 'active',
    # subscription.end_date > now(). Raise 403 if not premium.
    raise NotImplementedError
