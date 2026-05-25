"""
Alert service -- business logic for price and dividend alerts.

Core design:
  - Edge-trigger anti-spam: an alert fires ONLY when its condition
    TRANSITIONS from False to True. Staying True never re-fires.
  - FCM errors are caught and logged -- never crash the evaluation loop.
  - Pure functions (_evaluate_condition, _should_fire) are side-effect-free
    and fully unit-testable without a database.

FCM strategy: topic-based messaging (topic = "uid_{firebase_uid}").
The mobile app subscribes to this topic on login so the backend can push
without storing per-device FCM tokens.
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.models import Alert, DailyPrice, Dividend, Stock, User
from app.services.stock_service import get_latest_trading_date
from app.utils.exceptions import AlertNotFoundError, StockNotFoundError

logger = logging.getLogger(__name__)


# -- Notification helpers ------------------------------------------------------


def _format_fcfa(value: Decimal) -> str:
    """Format a Decimal as a French-style FCFA amount (e.g. '30 200 FCFA')."""
    return f"{int(value):,}".replace(",", " ") + " FCFA"


def _send_fcm_notification(
    firebase_uid: str,
    title: str,
    body: str,
) -> bool:
    """
    Send a FCM push notification to the user's device(s).

    Uses Firebase topic-based messaging: the mobile app subscribes to
    the topic "uid_{firebase_uid}" on login. This avoids storing per-device
    FCM registration tokens on the backend.

    Returns:
        True if the message was accepted by FCM, False on any error.

    Note:
        All exceptions are caught and logged so a single FCM failure
        never aborts the alert evaluation loop.
    """
    try:
        from firebase_admin import messaging  # deferred import -- testable

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            topic=f"uid_{firebase_uid}",
        )
        messaging.send(message)
        logger.info("FCM sent to uid=%s | %s", firebase_uid, body)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("FCM send failed for uid=%s: %s", firebase_uid, exc)
        return False


# -- Pure evaluation functions -------------------------------------------------


def _evaluate_condition(
    alert: Alert,
    close_price: Optional[Decimal],
    has_new_dividend: bool = False,
) -> bool:
    """
    Pure function -- evaluate whether the alert condition is currently met.

    Args:
        alert:            The Alert ORM object (read-only, no DB calls).
        close_price:      Latest closing price, or None if unavailable.
        has_new_dividend: True if a new dividend was detected for this stock.

    Returns:
        True if the condition is satisfied, False otherwise.
    """
    if alert.alert_type == "price_above":
        return (
            close_price is not None
            and alert.threshold is not None
            and close_price > alert.threshold
        )
    if alert.alert_type == "price_below":
        return (
            close_price is not None
            and alert.threshold is not None
            and close_price < alert.threshold
        )
    if alert.alert_type == "dividend":
        return has_new_dividend
    return False


def _should_fire(alert: Alert, condition_met: bool) -> bool:
    """
    Pure function -- edge-trigger logic.

    Returns True ONLY when the condition transitions False -> True.
    An alert that was already triggered (last_trigger_state=True) and
    whose condition is still True will NOT fire again.

    Truth table:
        last_trigger_state=False, condition=True  -> True  (FIRE)
        last_trigger_state=True,  condition=True  -> False (already fired)
        last_trigger_state=True,  condition=False -> False (reset handled separately)
        last_trigger_state=False, condition=False -> False (no change)
    """
    return condition_met and not alert.last_trigger_state


# -- Read helper ---------------------------------------------------------------


def build_alert_read(session: Session, alert: Alert) -> Dict[str, Any]:
    """
    Build an AlertRead-compatible dict from an Alert ORM object.

    Enriches the alert with symbol and stock_name from the Stock table.
    """
    stock = session.get(Stock, alert.stock_id)
    return {
        "id": alert.id,
        "symbol": stock.symbol if stock else "",
        "stock_name": stock.name if stock else "",
        "alert_type": alert.alert_type,
        "threshold": alert.threshold,
        "is_active": alert.is_active,
        "last_triggered_at": alert.last_triggered_at,
    }


# -- CRUD functions ------------------------------------------------------------


def create_alert(
    session: Session,
    user_id: int,
    symbol: str,
    alert_type: str,
    threshold: Optional[Decimal],
) -> Alert:
    """
    Create a new alert for the user.

    Raises:
        StockNotFoundError: if the symbol doesn't exist in the database.
    """
    stock = session.exec(
        select(Stock).where(Stock.symbol == symbol.upper())
    ).first()
    if not stock:
        raise StockNotFoundError(symbol)

    alert = Alert(
        user_id=user_id,
        stock_id=stock.id,
        alert_type=alert_type,
        threshold=threshold,
        is_active=True,
        last_trigger_state=False,
    )
    session.add(alert)
    session.commit()
    session.refresh(alert)
    logger.info(
        "Alert created: user=%d, stock=%s, type=%s, threshold=%s",
        user_id, symbol, alert_type, threshold,
    )
    return alert


def get_user_alerts(session: Session, user_id: int) -> List[Alert]:
    """Return all alerts for the user, ordered newest first."""
    return session.exec(
        select(Alert)
        .where(Alert.user_id == user_id)
        .order_by(Alert.created_at.desc())
    ).all()


def toggle_alert(
    session: Session,
    alert_id: int,
    user_id: int,
    is_active: bool,
) -> Alert:
    """
    Activate or deactivate an alert.

    When reactivating (is_active=True), last_trigger_state is reset to False
    so the alert can fire again if the condition is met.

    Raises:
        AlertNotFoundError: if the alert doesn't exist or belong to user.
    """
    alert = session.exec(
        select(Alert)
        .where(Alert.id == alert_id)
        .where(Alert.user_id == user_id)
    ).first()
    if not alert:
        raise AlertNotFoundError(alert_id)

    alert.is_active = is_active
    if is_active:
        # Reset edge-trigger state so the alert can fire immediately
        # if the condition is already met after reactivation.
        alert.last_trigger_state = False
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


def delete_alert(
    session: Session,
    alert_id: int,
    user_id: int,
) -> None:
    """
    Delete an alert.

    Raises:
        AlertNotFoundError: if the alert doesn't exist or belong to user.
    """
    alert = session.exec(
        select(Alert)
        .where(Alert.id == alert_id)
        .where(Alert.user_id == user_id)
    ).first()
    if not alert:
        raise AlertNotFoundError(alert_id)

    session.delete(alert)
    session.commit()
    logger.info("Alert %d deleted for user %d", alert_id, user_id)


# -- Scheduler helpers ---------------------------------------------------------


def _check_new_dividend(session: Session, alert: Alert) -> bool:
    """
    Return True if a new dividend has been detected for this stock since
    the alert last fired.

    A dividend is "new" when its fiscal_year is strictly greater than the
    year of the last trigger. An alert that has never fired considers any
    confirmed dividend as new.
    """
    latest_div = session.exec(
        select(Dividend)
        .where(Dividend.stock_id == alert.stock_id)
        .where(Dividend.is_confirmed == True)  # noqa: E712
        .order_by(Dividend.fiscal_year.desc())
    ).first()

    if not latest_div:
        return False
    if alert.last_triggered_at is None:
        return True  # first-ever trigger: any dividend qualifies
    return latest_div.fiscal_year > alert.last_triggered_at.year


def _get_latest_dividend_amount(
    session: Session, stock_id: int
) -> Optional[Decimal]:
    """Return the net_amount of the most recent confirmed dividend."""
    div = session.exec(
        select(Dividend)
        .where(Dividend.stock_id == stock_id)
        .where(Dividend.is_confirmed == True)  # noqa: E712
        .order_by(Dividend.fiscal_year.desc())
    ).first()
    return div.net_amount if div else None


# -- Main scheduler function ---------------------------------------------------


def check_and_fire_alerts(session: Session) -> int:
    """
    Evaluate all active alerts against the latest market prices and send
    FCM notifications where appropriate.

    Should be called once per day after the BOC/daily import completes.

    Algorithm:
        1. Fetch the latest trading_date from daily_prices.
        2. Load all active alerts.
        3. For each alert:
            a. Fetch the latest close_price for the alert's stock.
            b. Determine has_new_dividend (dividend alerts only).
            c. Evaluate condition with _evaluate_condition().
            d. Apply edge-trigger with _should_fire():
               - True  -> send FCM, set last_trigger_state=True,
                          update last_triggered_at if FCM succeeded.
               - False + state was True -> reset state to False.
        4. Commit all state changes atomically.
        5. Return count of FCM notifications successfully sent.

    FCM errors are caught per-alert -- one failure never blocks the others.
    """
    latest_date = get_latest_trading_date(session)

    active_alerts: List[Alert] = session.exec(
        select(Alert).where(Alert.is_active == True)  # noqa: E712
    ).all()

    notifications_sent = 0

    for alert in active_alerts:
        try:
            # Fetch latest price
            close_price: Optional[Decimal] = None
            if latest_date is not None:
                price_row = session.exec(
                    select(DailyPrice)
                    .where(DailyPrice.stock_id == alert.stock_id)
                    .where(DailyPrice.trading_date == latest_date)
                ).first()
                if price_row:
                    close_price = price_row.close_price

            # Determine dividend condition
            new_div = (
                _check_new_dividend(session, alert)
                if alert.alert_type == "dividend"
                else False
            )

            condition_met = _evaluate_condition(alert, close_price, new_div)

            if _should_fire(alert, condition_met):
                user = session.get(User, alert.user_id)
                stock = session.get(Stock, alert.stock_id)

                if user and stock:
                    # Build notification body
                    if alert.alert_type == "price_above" and close_price is not None and alert.threshold is not None:
                        fcm_body = (
                            f"{stock.symbol} depasse {_format_fcfa(alert.threshold)} "
                            f"(cours actuel : {_format_fcfa(close_price)})"
                        )
                    elif alert.alert_type == "price_below" and close_price is not None and alert.threshold is not None:
                        fcm_body = (
                            f"{stock.symbol} passe sous {_format_fcfa(alert.threshold)} "
                            f"(cours actuel : {_format_fcfa(close_price)})"
                        )
                    else:
                        div_amount = _get_latest_dividend_amount(session, alert.stock_id)
                        amount_str = _format_fcfa(div_amount) if div_amount else "un dividende"
                        fcm_body = f"{stock.symbol} : {amount_str} detache"

                    sent = _send_fcm_notification(
                        user.firebase_uid,
                        "Akwaba Invest - Alerte",
                        fcm_body,
                    )
                    if sent:
                        alert.last_triggered_at = datetime.utcnow()
                        notifications_sent += 1

                # Always set state True to prevent double-fire,
                # even when FCM failed or user/stock not found.
                alert.last_trigger_state = True
                session.add(alert)

            elif not condition_met and alert.last_trigger_state:
                # Condition dropped to False -- reset so alert can fire again
                # next time the condition is True (new transition).
                alert.last_trigger_state = False
                session.add(alert)

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error processing alert %d: %s",
                alert.id, exc, exc_info=True,
            )

    session.commit()
    logger.info(
        "check_and_fire_alerts complete -- %d notification(s) sent / %d active alert(s)",
        notifications_sent, len(active_alerts),
    )
    return notifications_sent
