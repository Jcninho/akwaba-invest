import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.dependencies import require_premium

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/")
async def get_portfolio(user: str = Depends(require_premium), session: Session = Depends(get_session)):
    # TODO: return user portfolio with current value and Total Return
    raise NotImplementedError


@router.post("/lines")
async def add_portfolio_line(user: str = Depends(require_premium), session: Session = Depends(get_session)):
    # TODO: add a position; compute and persist consolidated PRU
    raise NotImplementedError


@router.delete("/lines/{line_id}")
async def delete_portfolio_line(line_id: int, user: str = Depends(require_premium), session: Session = Depends(get_session)):
    # TODO: remove position and recompute portfolio metrics
    raise NotImplementedError
