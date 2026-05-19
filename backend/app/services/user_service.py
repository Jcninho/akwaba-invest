import logging
from datetime import date, datetime
from typing import Optional

from sqlmodel import Session, select

from app.models import Subscription, User

logger = logging.getLogger(__name__)


def upsert_user(
    session: Session,
    firebase_uid: str,
    email: str,
) -> User:
    """Create user if not exists, otherwise return existing."""
    existing = session.exec(
        select(User).where(User.firebase_uid == firebase_uid)
    ).first()
    if existing:
        logger.info(f"User already exists: {email}")
        return existing

    user = User(firebase_uid=firebase_uid, email=email, plan="free")
    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"User created: {email}")
    return user


def get_active_subscription_end_date(
    session: Session,
    user_id: int,
) -> Optional[datetime]:
    """Return end_date of active subscription if any."""
    today = date.today()
    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .where(Subscription.status == "active")
        .where(Subscription.end_date >= today)
        .order_by(Subscription.end_date.desc())
    ).first()
    if sub:
        return datetime.combine(sub.end_date, datetime.min.time())
    return None
