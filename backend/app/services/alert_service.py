import logging

from sqlmodel import Session

logger = logging.getLogger(__name__)


def get_user_alerts(user_id: str, session: Session) -> list:
    # TODO: query alerts for user, return list
    raise NotImplementedError


def create_alert(user_id: str, ticker: str, condition: dict, session: Session) -> dict:
    # TODO: persist alert with last_trigger_state=False; raise if duplicate
    raise NotImplementedError


def delete_alert(user_id: str, alert_id: int, session: Session) -> None:
    # TODO: verify ownership before deletion; raise 404 if not found
    raise NotImplementedError


def evaluate_alerts(session: Session) -> None:
    # TODO: for each active alert, check condition against latest price;
    # send FCM only when last_trigger_state transitions False -> True (edge-trigger)
    raise NotImplementedError
