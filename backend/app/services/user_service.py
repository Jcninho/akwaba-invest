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
    """
    Create or update user from Firebase identity.

    Handles three cases:
    1. Existing user matched by firebase_uid → return as-is
    2. Existing user matched by email (Firebase account recreated with
       a new UID) → update firebase_uid to the new value
    3. No match → create new user
    """
    # Case 1: match by firebase_uid
    existing = session.exec(
        select(User).where(User.firebase_uid == firebase_uid)
    ).first()
    if existing:
        logger.info("User found by firebase_uid: %s", email)
        return existing

    # Case 2: match by email (account recreated with new UID)
    if email:
        by_email = session.exec(
            select(User).where(User.email == email)
        ).first()
        if by_email:
            logger.info(
                "User found by email, updating firebase_uid: %s", email
            )
            by_email.firebase_uid = firebase_uid
            by_email.updated_at = datetime.utcnow()
            session.add(by_email)
            session.commit()
            session.refresh(by_email)
            return by_email

    # Case 3: new user
    user = User(firebase_uid=firebase_uid, email=email, plan="free")
    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info("User created: %s", email)
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
