import logging

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.database import get_session
from app.dependencies import verify_firebase_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/subscribe")
async def initiate_subscription(user: str = Depends(verify_firebase_token), session: Session = Depends(get_session)):
    # TODO: create Wave Business payment link for monthly/annual plan
    raise NotImplementedError


@router.post("/webhook/wave")
async def wave_webhook(request: Request, session: Session = Depends(get_session)):
    # TODO: verify HMAC signature before any processing; upgrade user to premium
    raise NotImplementedError


@router.get("/status")
async def subscription_status(user: str = Depends(verify_firebase_token), session: Session = Depends(get_session)):
    # TODO: return current subscription plan and expiry date
    raise NotImplementedError
