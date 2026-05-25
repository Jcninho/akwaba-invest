"""
Integration tests for /api/v1/portfolio routes.

Setup:
  - In-memory SQLite database seeded with two stocks (SNTS with price, NTLC without).
  - get_current_user overridden to return a deterministic test User.
  - Firebase init patched so no credentials file is needed.

Seeded data:
  SNTS — SONATEL SN, Télécommunications, close=28 800 FCFA on 2026-05-25
  NTLC — NESTLE CI, Consommation, no price row
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.dependencies import get_current_user
from app.main import app
from app.models import DailyPrice, Portfolio, PortfolioLine, Stock, User

TRADING_DATE = date(2026, 5, 25)
BASE_URL = "/api/v1/portfolio"


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
    Seed DB with a test user, two stocks, and one price row.

    Returns (session, user, snts_stock, ntlc_stock).
    """
    user = User(firebase_uid="test_uid", email="test@akwaba.test", plan="free")
    session.add(user)
    session.flush()

    snts = Stock(symbol="SNTS", name="SONATEL SN", sector="Télécommunications", country="SN", is_active=True)
    ntlc = Stock(symbol="NTLC", name="NESTLE CI", sector="Consommation", country="CI", is_active=True)
    session.add_all([snts, ntlc])
    session.flush()

    session.add(
        DailyPrice(
            stock_id=snts.id,
            trading_date=TRADING_DATE,
            close_price=Decimal("28800.00"),
            open_price=Decimal("28850.00"),
            volume=14844,
            variation_pct=Decimal("-0.35"),
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


# ── GET /portfolio/ ───────────────────────────────────────────────────────────


def test_get_portfolio_creates_default_if_none(client: TestClient, seeded) -> None:
    """First GET with no portfolio → auto-create 'Mon portefeuille'."""
    session, user, *_ = seeded
    # Verify no portfolio exists yet
    assert session.exec(
        __import__("sqlmodel", fromlist=["select"]).select(Portfolio)
        .where(Portfolio.user_id == user.id)
    ).first() is None

    response = client.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Mon portefeuille"
    assert data["lines"] == []
    # Decimal("0") is serialised as the string "0" by FastAPI/Pydantic JSON mode
    assert float(data["total_cost"]) == pytest.approx(0.0)
    assert data["total_value"] is None


def test_get_portfolio_returns_existing(client: TestClient, seeded) -> None:
    """Second GET returns the same portfolio, not a new one."""
    client.get(f"{BASE_URL}/")  # creates it
    client.get(f"{BASE_URL}/")  # should reuse

    session, user, *_ = seeded
    from sqlmodel import select
    portfolios = session.exec(
        select(Portfolio).where(Portfolio.user_id == user.id)
    ).all()
    assert len(portfolios) == 1  # exactly one, not two


# ── POST /portfolio/lines ─────────────────────────────────────────────────────


def test_add_line_creates_new_position(client: TestClient) -> None:
    response = client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 10, "price": 28800},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["lines"]) == 1
    line = data["lines"][0]
    assert line["symbol"] == "SNTS"
    assert line["stock_name"] == "SONATEL SN"
    assert float(line["quantity"]) == pytest.approx(10.0)
    assert float(line["avg_price"]) == pytest.approx(28800.0)


def test_add_line_consolidates_pru(client: TestClient) -> None:
    """Two buys of the same stock → PRU consolidated, quantity added."""
    # First buy: 10 @ 28 800
    client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 10, "price": 28800},
    )
    # Second buy: 10 @ 29 000
    response = client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 10, "price": 29000},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["lines"]) == 1  # still one line, not two
    line = data["lines"][0]
    assert float(line["quantity"]) == pytest.approx(20.0)
    # PRU = (10×28800 + 10×29000) / 20 = 28900
    assert float(line["avg_price"]) == pytest.approx(28900.0)


def test_pru_calculation_correct(client: TestClient) -> None:
    """
    PRU for an asymmetric buy: 10 @ 1 000 + 5 @ 1 200 → exact = 1 066.666…
    The DB column (decimal_places=2) stores 1 066.67 after rounding.
    """
    client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 10, "price": 1000},
    )
    response = client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 5, "price": 1200},
    )
    assert response.status_code == 200
    line = response.json()["lines"][0]
    # Exact mathematical result before DB rounding
    exact = (Decimal("10") * Decimal("1000") + Decimal("5") * Decimal("1200")) / Decimal("15")
    # DB stores with 2 decimal places → 1066.67
    assert float(line["avg_price"]) == pytest.approx(float(exact), rel=1e-4)


def test_add_line_stock_not_found_returns_404(client: TestClient) -> None:
    response = client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "XXNOTFOUND", "quantity": 10, "price": 1000},
    )
    assert response.status_code == 404
    assert "XXNOTFOUND" in response.json()["detail"]


def test_add_line_zero_quantity_returns_422(client: TestClient) -> None:
    response = client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 0, "price": 1000},
    )
    assert response.status_code == 422


def test_add_line_negative_price_returns_422(client: TestClient) -> None:
    response = client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 10, "price": -100},
    )
    assert response.status_code == 422


# ── DELETE /portfolio/lines/{line_id} ─────────────────────────────────────────


def test_remove_line_success(client: TestClient) -> None:
    # Add a position
    add_resp = client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 10, "price": 28800},
    )
    line_id = add_resp.json()["lines"][0]["id"]

    # Remove it
    response = client.delete(f"{BASE_URL}/lines/{line_id}")
    assert response.status_code == 200
    assert response.json()["lines"] == []


def test_remove_line_not_found_returns_404(client: TestClient) -> None:
    response = client.delete(f"{BASE_URL}/lines/99999")
    assert response.status_code == 404


# ── POST /portfolio/dividends ─────────────────────────────────────────────────


def test_record_dividends_updates_total(client: TestClient) -> None:
    # Add 10 shares of SNTS
    client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 10, "price": 28800},
    )
    # Record 1 655 FCFA/share
    response = client.post(
        f"{BASE_URL}/dividends",
        json={"symbol": "SNTS", "amount_per_share": 1655},
    )
    assert response.status_code == 200
    line = response.json()["lines"][0]
    # total_dividends = 10 × 1655 = 16 550
    assert float(line["total_dividends_received"]) == pytest.approx(16550.0)


def test_record_dividends_affects_total_return(client: TestClient) -> None:
    client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 10, "price": 28800},
    )
    response = client.post(
        f"{BASE_URL}/dividends",
        json={"symbol": "SNTS", "amount_per_share": 1655},
    )
    line = response.json()["lines"][0]
    # unrealized_gain = (28800 - 28800) × 10 = 0  (bought at current price)
    # total_return = unrealized_gain + dividends = 0 + 16550 = 16550
    assert line["total_return"] is not None
    assert float(line["total_return"]) == pytest.approx(16550.0)


def test_record_dividends_stock_not_found_returns_404(client: TestClient) -> None:
    response = client.post(
        f"{BASE_URL}/dividends",
        json={"symbol": "XXNOTFOUND", "amount_per_share": 100},
    )
    assert response.status_code == 404


def test_record_dividends_no_position_returns_404(client: TestClient) -> None:
    """NTLC is a valid stock but has no position → 404."""
    response = client.post(
        f"{BASE_URL}/dividends",
        json={"symbol": "NTLC", "amount_per_share": 100},
    )
    assert response.status_code == 404


# ── Portfolio valuation ───────────────────────────────────────────────────────


def test_portfolio_valuation_with_price(client: TestClient) -> None:
    """SNTS has a price → current_value and unrealized_gain are computed."""
    client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 10, "price": 27000},
    )
    response = client.get(f"{BASE_URL}/")
    data = response.json()
    line = data["lines"][0]

    assert line["current_price"] is not None
    assert float(line["current_price"]) == pytest.approx(28800.0)
    # current_value = 10 × 28800 = 288000
    assert float(line["current_value"]) == pytest.approx(288000.0)
    # cost_basis = 10 × 27000 = 270000
    assert float(line["cost_basis"]) == pytest.approx(270000.0)
    # unrealized_gain = 288000 - 270000 = 18000
    assert float(line["unrealized_gain"]) == pytest.approx(18000.0)
    # unrealized_gain_pct = 18000/270000 × 100 ≈ 6.6667
    assert float(line["unrealized_gain_pct"]) == pytest.approx(100 * 18000 / 270000)


def test_portfolio_valuation_without_price(client: TestClient) -> None:
    """NTLC has no price row → current_value and unrealized_gain are null."""
    client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "NTLC", "quantity": 5, "price": 12000},
    )
    response = client.get(f"{BASE_URL}/")
    data = response.json()
    line = data["lines"][0]

    assert line["current_price"] is None
    assert line["current_value"] is None
    assert line["unrealized_gain"] is None
    assert line["unrealized_gain_pct"] is None
    assert line["total_return"] is None
    # Portfolio totals should also be None (no priced lines)
    assert data["total_value"] is None
    assert data["total_gain"] is None


def test_portfolio_totals_computed_correctly(client: TestClient) -> None:
    """Verify portfolio-level total_value, total_cost, total_gain."""
    # Buy SNTS @ 27 000 — current price is 28 800
    client.post(
        f"{BASE_URL}/lines",
        json={"symbol": "SNTS", "quantity": 10, "price": 27000},
    )
    response = client.get(f"{BASE_URL}/")
    data = response.json()

    # total_cost = 10 × 27000 = 270000
    assert float(data["total_cost"]) == pytest.approx(270000.0)
    # total_value = 10 × 28800 = 288000
    assert float(data["total_value"]) == pytest.approx(288000.0)
    # total_gain = 288000 - 270000 = 18000
    assert float(data["total_gain"]) == pytest.approx(18000.0)
    # total_gain_pct ≈ 6.6667%
    assert float(data["total_gain_pct"]) == pytest.approx(100 * 18000 / 270000)


# ── GET/POST /portfolio/portfolios ────────────────────────────────────────────


def test_create_portfolio_success(client: TestClient) -> None:
    response = client.post(
        f"{BASE_URL}/portfolios",
        json={"name": "Tech Africa"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Tech Africa"
    assert "id" in data


def test_list_portfolios_returns_all(client: TestClient) -> None:
    # Create two portfolios (GET / auto-creates the default)
    client.get(f"{BASE_URL}/")
    client.post(f"{BASE_URL}/portfolios", json={"name": "Tech Africa"})
    client.post(f"{BASE_URL}/portfolios", json={"name": "Dividendes"})

    response = client.get(f"{BASE_URL}/portfolios")
    assert response.status_code == 200
    portfolios = response.json()
    assert len(portfolios) == 3  # default + 2 created
    names = {p["name"] for p in portfolios}
    assert "Mon portefeuille" in names
    assert "Tech Africa" in names
    assert "Dividendes" in names


def test_list_portfolios_empty_before_any_action(client: TestClient) -> None:
    response = client.get(f"{BASE_URL}/portfolios")
    assert response.status_code == 200
    assert response.json() == []


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_add_multiple_different_stocks(client: TestClient) -> None:
    """Two different stocks → two distinct lines."""
    client.post(f"{BASE_URL}/lines", json={"symbol": "SNTS", "quantity": 10, "price": 28800})
    response = client.post(f"{BASE_URL}/lines", json={"symbol": "NTLC", "quantity": 5, "price": 12000})
    assert response.status_code == 200
    assert len(response.json()["lines"]) == 2


def test_portfolio_last_updated_set_when_price_exists(client: TestClient) -> None:
    """last_updated should reflect the trading date of the price used."""
    client.post(f"{BASE_URL}/lines", json={"symbol": "SNTS", "quantity": 10, "price": 28800})
    response = client.get(f"{BASE_URL}/")
    assert response.json()["last_updated"] == str(TRADING_DATE)


def test_portfolio_last_updated_none_without_prices(client: TestClient) -> None:
    """No price rows at all → last_updated is null."""
    client.post(f"{BASE_URL}/lines", json={"symbol": "NTLC", "quantity": 5, "price": 12000})
    response = client.get(f"{BASE_URL}/")
    assert response.json()["last_updated"] is None


def test_record_dividends_zero_amount_returns_422(client: TestClient) -> None:
    response = client.post(
        f"{BASE_URL}/dividends",
        json={"symbol": "SNTS", "amount_per_share": 0},
    )
    assert response.status_code == 422
