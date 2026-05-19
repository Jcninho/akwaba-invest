import logging

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.config import settings

logger = logging.getLogger(__name__)

_firebase_app = None


def init_firebase() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is None:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized")
    return _firebase_app


def verify_id_token(token: str) -> dict:
    """Verify Firebase ID token and return decoded claims."""
    init_firebase()
    return firebase_auth.verify_id_token(token)
