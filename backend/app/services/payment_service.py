import logging
import secrets

from sqlmodel import Session

logger = logging.getLogger(__name__)


def initiate_wave_subscription(user_id: str, plan: str, session: Session) -> dict:
    # TODO: call Wave Business API to create payment link; persist pending subscription
    raise NotImplementedError


def verify_wave_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    # Use secrets.compare_digest to prevent timing attacks
    # TODO: compute HMAC-SHA256 of payload with secret; compare with signature
    raise NotImplementedError


def upgrade_user_to_premium(user_id: str, plan: str, session: Session) -> None:
    # TODO: set user.plan = 'premium', upsert subscription with status=active and end_date
    raise NotImplementedError


def get_subscription_status(user_id: str, session: Session) -> dict:
    # TODO: return current plan, status, end_date for the user
    raise NotImplementedError
