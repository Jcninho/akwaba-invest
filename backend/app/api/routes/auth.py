import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
async def get_token():
    # TODO: exchange Firebase ID token for session; return access token
    raise NotImplementedError


@router.post("/refresh")
async def refresh_token():
    # TODO: refresh expired session token via Firebase
    raise NotImplementedError


@router.delete("/logout")
async def logout():
    # TODO: revoke session token and clear server-side state
    raise NotImplementedError
