"""
Tests for P1-10 -- /alerts routes and alert_service business logic.

Structure:
  Part 1 -- Route integration tests (11 tests)
  Part 2 -- Pure function unit tests (10 tests)
  Part 3 -- check_and_fire_alerts scheduler tests (4 tests)

Seeded data:
  User  -- firebase_uid="test_uid", plan="free"
  SNTS  -- SONATEL SN, close=30000 FCFA on 2026-05-25
  NTLC  -- NESTLE CI (no price row)
  Dividend -- SNTS, fiscal_year=2025, net_amount=1655, is_confirmed=True
"""
import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.dependencies import get_current_user
from app.main import app
from app.models import Alert, DailyPrice, Dividend, Stock, User
from app.services.alert_service import (
    _evaluate_condition,
    _should_fire,
    check_and_fire_alerts,
    create_alert,
)

TRADING_DATE = date(2026, 5, 25)
BASE_URL = "/api/v1/alerts"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="seeded")
def seeded_fixture(session: Session):
    """
    Seed DB with a user, two stocks, one price row, and one confirmed dividend.

    Returns (session, user, snts_stock, ntlc_stock).
    """
    user = User(firebase_uid="test_uid", email="test@akwaba.test", plan="free")
    session.add(user)
    session.flush()

    snts = Stock(
        symbol="SNTS",
        name="SONATEL SN",
        sector="Telecommunications",
        country="SN",
        is_active=True,
    )
    ntlc = Stock(
        symbol="NTLC",
        name="NESTLE CI",
        sector="Consommation",
        country="CI",
        is_active=True,
    )
    session.add_all([snts, ntlc])
    session.flush()

    session.add(
        DailyPrice(
            stock_id=snts.id,
            trading_date=TRADING_DATE,
            close_price=Decimal("30000.00"),
            open_price=Decimal("30100.00"),
            volume=5000,
            variation_pct=Decimal("-0.33"),
        )
    )
    session.add(
        Dividend(
            stock_id=snts.id,
            fiscal_year=2025,
            gross_amount=Decimal("2000.00"),
            net_amount=Decimal("1655.00"),
            is_confirmed=True,
        )
    )
    session.commit()
    return session, user, snts, ntlc


@pytest.fixture(name="client")
def client_fixture(seeded):
    session, user, _snts, _ntlc = seeded

    def override_get_session():
        yield session

    def override_get_current_user():
        return user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    with patch("app.main.init_firebase"):
        with TestClient(app) as client:
            yield client

    app.dependency_overrides.clear()


# ── Part 1: Route integration tests ───────────────────────────────────────────


class TestListAlerts:
    def test_empty_list_returns_200(self, client: TestClient) -> None:
        response = client.get(f"{BASE_URL}/")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_created_alerts(self, client: TestClient) -> None:
        client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_above", "threshold": 35000},
        )
        response = client.get(f"{BASE_URL}/")
        assert response.status_code == 200
        alerts = response.json()
        assert len(alerts) == 1
        assert alerts[0]["symbol"] == "SNTS"
        assert alerts[0]["alert_type"] == "price_above"
        assert float(alerts[0]["threshold"]) == pytest.approx(35000.0)
        assert alerts[0]["is_active"] is True


class TestCreateAlert:
    def test_price_above_created_successfully(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_above", "threshold": 35000},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "SNTS"
        assert data["stock_name"] == "SONATEL SN"
        assert data["alert_type"] == "price_above"
        assert float(data["threshold"]) == pytest.approx(35000.0)
        assert data["is_active"] is True
        assert data["last_triggered_at"] is None

    def test_price_below_created_successfully(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_below", "threshold": 25000},
        )
        assert response.status_code == 201
        assert response.json()["alert_type"] == "price_below"

    def test_dividend_alert_no_threshold_needed(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "dividend"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["alert_type"] == "dividend"
        assert data["threshold"] is None

    def test_unknown_symbol_returns_404(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE_URL}/",
            json={"symbol": "XXNOTFOUND", "alert_type": "price_above", "threshold": 1000},
        )
        assert response.status_code == 404
        assert "XXNOTFOUND" in response.json()["detail"]

    def test_price_alert_without_threshold_returns_422(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_above"},
        )
        assert response.status_code == 422

    def test_invalid_alert_type_returns_422(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_sideways", "threshold": 1000},
        )
        assert response.status_code == 422

    def test_zero_threshold_returns_422(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_above", "threshold": 0},
        )
        assert response.status_code == 422

    def test_negative_threshold_returns_422(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_above", "threshold": -100},
        )
        assert response.status_code == 422


class TestDeleteAlert:
    def test_delete_existing_alert_returns_204(self, client: TestClient) -> None:
        create_resp = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_above", "threshold": 35000},
        )
        alert_id = create_resp.json()["id"]
        response = client.delete(f"{BASE_URL}/{alert_id}")
        assert response.status_code == 204

    def test_deleted_alert_not_in_list(self, client: TestClient) -> None:
        create_resp = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_above", "threshold": 35000},
        )
        alert_id = create_resp.json()["id"]
        client.delete(f"{BASE_URL}/{alert_id}")
        assert client.get(f"{BASE_URL}/").json() == []

    def test_delete_nonexistent_returns_404(self, client: TestClient) -> None:
        response = client.delete(f"{BASE_URL}/99999")
        assert response.status_code == 404


class TestToggleAlert:
    def test_deactivate_active_alert(self, client: TestClient) -> None:
        create_resp = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_above", "threshold": 35000},
        )
        alert_id = create_resp.json()["id"]
        response = client.patch(f"{BASE_URL}/{alert_id}/toggle", json={"is_active": False})
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_reactivate_deactivated_alert(self, client: TestClient) -> None:
        create_resp = client.post(
            f"{BASE_URL}/",
            json={"symbol": "SNTS", "alert_type": "price_above", "threshold": 35000},
        )
        alert_id = create_resp.json()["id"]
        client.patch(f"{BASE_URL}/{alert_id}/toggle", json={"is_active": False})
        response = client.patch(f"{BASE_URL}/{alert_id}/toggle", json={"is_active": True})
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_toggle_nonexistent_returns_404(self, client: TestClient) -> None:
        response = client.patch(f"{BASE_URL}/99999/toggle", json={"is_active": False})
        assert response.status_code == 404


# ── Part 2: Pure function unit tests ─────────────────────────────────────────


class TestEvaluateCondition:
    """Tests for _evaluate_condition -- pure, no DB.

    Uses SimpleNamespace to avoid SQLModel/SQLAlchemy ORM overhead:
    _evaluate_condition only reads alert.alert_type and alert.threshold.
    """

    def _make_alert(self, alert_type: str, threshold=None):
        from types import SimpleNamespace
        return SimpleNamespace(
            alert_type=alert_type,
            threshold=Decimal(str(threshold)) if threshold is not None else None,
            last_trigger_state=False,
        )

    def test_price_above_true_when_exceeds(self) -> None:
        alert = self._make_alert("price_above", 30000)
        assert _evaluate_condition(alert, Decimal("30001")) is True

    def test_price_above_false_when_equal(self) -> None:
        alert = self._make_alert("price_above", 30000)
        assert _evaluate_condition(alert, Decimal("30000")) is False

    def test_price_above_false_when_below(self) -> None:
        alert = self._make_alert("price_above", 30000)
        assert _evaluate_condition(alert, Decimal("29999")) is False

    def test_price_below_true_when_below(self) -> None:
        alert = self._make_alert("price_below", 25000)
        assert _evaluate_condition(alert, Decimal("24999")) is True

    def test_price_below_false_when_equal(self) -> None:
        alert = self._make_alert("price_below", 25000)
        assert _evaluate_condition(alert, Decimal("25000")) is False

    def test_price_above_false_when_no_price(self) -> None:
        alert = self._make_alert("price_above", 30000)
        assert _evaluate_condition(alert, None) is False

    def test_dividend_true_when_new_dividend(self) -> None:
        alert = self._make_alert("dividend")
        assert _evaluate_condition(alert, None, has_new_dividend=True) is True

    def test_dividend_false_when_no_new_dividend(self) -> None:
        alert = self._make_alert("dividend")
        assert _evaluate_condition(alert, None, has_new_dividend=False) is False

    def test_unknown_type_returns_false(self) -> None:
        alert = self._make_alert("price_sideways", 30000)
        assert _evaluate_condition(alert, Decimal("30001")) is False


class TestShouldFire:
    """Tests for _should_fire -- pure edge-trigger logic."""

    def _make_alert(self, last_trigger_state: bool):
        from types import SimpleNamespace
        return SimpleNamespace(last_trigger_state=last_trigger_state)

    def test_fires_on_false_to_true_transition(self) -> None:
        """FALSE -> TRUE: must fire."""
        alert = self._make_alert(last_trigger_state=False)
        assert _should_fire(alert, condition_met=True) is True

    def test_does_not_refire_when_already_triggered(self) -> None:
        """TRUE -> TRUE: anti-spam, must NOT fire."""
        alert = self._make_alert(last_trigger_state=True)
        assert _should_fire(alert, condition_met=True) is False

    def test_does_not_fire_when_condition_false_state_false(self) -> None:
        """FALSE -> FALSE: no change."""
        alert = self._make_alert(last_trigger_state=False)
        assert _should_fire(alert, condition_met=False) is False

    def test_does_not_fire_when_condition_false_state_true(self) -> None:
        """TRUE -> FALSE: reset handled elsewhere, not a fire event."""
        alert = self._make_alert(last_trigger_state=True)
        assert _should_fire(alert, condition_met=False) is False


# ── Part 3: check_and_fire_alerts scheduler tests ────────────────────────────


class TestCheckAndFireAlerts:
    """
    Integration tests for check_and_fire_alerts.

    FCM send is always mocked -- no real Firebase calls.
    """

    def test_price_above_fires_when_threshold_crossed(self, seeded) -> None:
        session, user, snts, _ntlc = seeded
        # threshold=25000, current close=30000 -> condition True, state False -> FIRES
        alert = create_alert(session, user.id, "SNTS", "price_above", Decimal("25000"))

        with patch(
            "app.services.alert_service._send_fcm_notification",
            return_value=True,
        ) as mock_fcm:
            count = check_and_fire_alerts(session)

        assert count == 1
        mock_fcm.assert_called_once()
        session.refresh(alert)
        assert alert.last_trigger_state is True
        assert alert.last_triggered_at is not None

    def test_price_above_no_refire_when_already_triggered(self, seeded) -> None:
        """Edge-trigger: second call with same True condition must NOT re-fire."""
        session, user, snts, _ntlc = seeded
        create_alert(session, user.id, "SNTS", "price_above", Decimal("25000"))

        with patch(
            "app.services.alert_service._send_fcm_notification",
            return_value=True,
        ):
            first = check_and_fire_alerts(session)

        with patch(
            "app.services.alert_service._send_fcm_notification",
            return_value=True,
        ) as mock_second:
            second = check_and_fire_alerts(session)

        assert first == 1
        assert second == 0
        mock_second.assert_not_called()

    def test_no_notification_when_condition_not_met(self, seeded) -> None:
        """price_above 40000 > current close 30000 -> no fire."""
        session, user, snts, _ntlc = seeded
        create_alert(session, user.id, "SNTS", "price_above", Decimal("40000"))

        with patch(
            "app.services.alert_service._send_fcm_notification",
            return_value=True,
        ) as mock_fcm:
            count = check_and_fire_alerts(session)

        assert count == 0
        mock_fcm.assert_not_called()

    def test_fcm_failure_sets_state_but_does_not_count(self, seeded) -> None:
        """
        Even if FCM fails, last_trigger_state must be set True to prevent
        double-fire. The notification count should NOT increment.
        """
        session, user, snts, _ntlc = seeded
        alert = create_alert(session, user.id, "SNTS", "price_above", Decimal("25000"))

        with patch(
            "app.services.alert_service._send_fcm_notification",
            return_value=False,  # FCM fails
        ):
            count = check_and_fire_alerts(session)

        assert count == 0  # not counted when FCM fails
        session.refresh(alert)
        assert alert.last_trigger_state is True  # still set to prevent double-fire
