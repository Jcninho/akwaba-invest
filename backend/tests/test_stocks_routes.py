"""
Integration tests for /api/v1/stocks routes.

Uses FastAPI TestClient + in-memory SQLite. Firebase init and the
require_premium dependency are mocked so the test suite runs without
external services.

Seeded data (2 stocks):
  SNTS — Télécommunications, variation -0.35 % (loser)
  NTLC — Consommation de Base, variation +1.70 % (gainer)
  Both priced on 2026-05-25.
  SNTS has one dividend (2025) and one financial record (2024).
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.dependencies import require_premium
from app.main import app
from app.models import DailyPrice, Dividend, Financial, Stock, User

# ── Fixtures ──────────────────────────────────────────────────────────────────

TRADING_DATE = date(2026, 5, 25)


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


@pytest.fixture(name="seeded_session")
def seeded_session_fixture(session: Session) -> Session:
    """Seed two stocks with prices, one dividend, and one financial record."""
    snts = Stock(
        symbol="SNTS",
        name="SONATEL SN",
        sector="Télécommunications",
        country="SN",
        is_active=True,
    )
    ntlc = Stock(
        symbol="NTLC",
        name="NESTLE CI",
        sector="Consommation de Base",
        country="CI",
        is_active=True,
    )
    session.add_all([snts, ntlc])
    session.flush()

    # Daily prices — SNTS down, NTLC up
    session.add(
        DailyPrice(
            stock_id=snts.id,
            trading_date=TRADING_DATE,
            close_price=Decimal("28800.00"),
            open_price=Decimal("28850.00"),
            high_price=Decimal("29000.00"),
            low_price=Decimal("28700.00"),
            volume=14844,
            variation_pct=Decimal("-0.35"),
        )
    )
    session.add(
        DailyPrice(
            stock_id=ntlc.id,
            trading_date=TRADING_DATE,
            close_price=Decimal("11950.00"),
            open_price=Decimal("11750.00"),
            high_price=Decimal("12000.00"),
            low_price=Decimal("11700.00"),
            volume=686,
            variation_pct=Decimal("1.70"),
        )
    )

    # Dividend — SNTS only
    session.add(
        Dividend(
            stock_id=snts.id,
            fiscal_year=2025,
            gross_amount=Decimal("1655.00"),
            net_amount=Decimal("1655.00"),
            payment_date=date(2025, 5, 22),
            is_confirmed=True,
        )
    )

    # Financials — SNTS only
    session.add(
        Financial(
            stock_id=snts.id,
            fiscal_year=2024,
            revenue=450_000_000,
            net_income=80_000_000,
            total_debt=50_000_000,
            equity=300_000_000,
        )
    )

    session.commit()
    return session


@pytest.fixture(name="client")
def client_fixture(seeded_session: Session):
    """
    TestClient with:
    - get_session overridden to use the in-memory seeded DB
    - require_premium overridden to always pass (returns a mock premium user)
    - Firebase init patched to avoid credentials file requirement
    """

    def override_get_session():
        yield seeded_session

    def override_require_premium():
        return User(
            firebase_uid="test_uid",
            email="premium@test.com",
            plan="premium",
        )

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[require_premium] = override_require_premium

    with patch("app.main.init_firebase"):
        with TestClient(app) as client:
            yield client

    app.dependency_overrides.clear()


# ── GET /stocks/ ──────────────────────────────────────────────────────────────


def test_list_stocks_returns_all(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    symbols = {s["symbol"] for s in data}
    assert symbols == {"SNTS", "NTLC"}


def test_list_stocks_fields(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/")
    stock = next(s for s in response.json() if s["symbol"] == "SNTS")
    assert stock["name"] == "SONATEL SN"
    assert stock["sector"] == "Télécommunications"
    assert float(stock["close_price"]) == pytest.approx(28800.0)
    assert stock["trading_date"] == str(TRADING_DATE)


def test_list_stocks_sector_filter(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/?sector=T%C3%A9l%C3%A9communications")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "SNTS"


def test_list_stocks_sector_filter_no_match(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/?sector=Banques")
    assert response.status_code == 200
    assert response.json() == []


# ── GET /stocks/summary ───────────────────────────────────────────────────────


def test_market_summary_fields(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_stocks"] == 2
    assert data["stocks_up"] == 1    # NTLC +1.70%
    assert data["stocks_down"] == 1  # SNTS -0.35%
    assert data["stocks_unchanged"] == 0
    assert data["trading_date"] == str(TRADING_DATE)


def test_market_summary_top_gainers(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/summary")
    data = response.json()
    assert len(data["top_gainers"]) >= 1
    assert data["top_gainers"][0]["symbol"] == "NTLC"


def test_market_summary_top_losers(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/summary")
    data = response.json()
    assert len(data["top_losers"]) >= 1
    assert data["top_losers"][0]["symbol"] == "SNTS"


# ── GET /stocks/search ────────────────────────────────────────────────────────


def test_search_by_symbol(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/search?q=SN")
    assert response.status_code == 200
    symbols = {s["symbol"] for s in response.json()}
    assert "SNTS" in symbols


def test_search_by_name(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/search?q=nestle")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "NTLC"


def test_search_case_insensitive(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/search?q=sonatel")
    assert response.status_code == 200
    data = response.json()
    assert any(s["symbol"] == "SNTS" for s in data)


def test_search_too_short_returns_422(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/search?q=S")
    assert response.status_code == 422


def test_search_no_match_returns_empty(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/search?q=XXNOTFOUND")
    assert response.status_code == 200
    assert response.json() == []


# ── GET /stocks/top-movers ────────────────────────────────────────────────────


def test_top_movers_structure(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/top-movers")
    assert response.status_code == 200
    data = response.json()
    assert "gainers" in data
    assert "losers" in data
    assert "trading_date" in data


def test_top_movers_gainer_is_ntlc(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/top-movers")
    data = response.json()
    assert len(data["gainers"]) >= 1
    assert data["gainers"][0]["symbol"] == "NTLC"


def test_top_movers_loser_is_snts(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/top-movers")
    data = response.json()
    assert len(data["losers"]) >= 1
    assert data["losers"][0]["symbol"] == "SNTS"


def test_top_movers_with_date_param(client: TestClient) -> None:
    response = client.get(f"/api/v1/stocks/top-movers?date={TRADING_DATE}")
    assert response.status_code == 200
    data = response.json()
    assert data["trading_date"] == str(TRADING_DATE)


def test_top_movers_empty_date_returns_no_data(client: TestClient) -> None:
    """A date with no data should return empty lists (not 404)."""
    response = client.get("/api/v1/stocks/top-movers?date=2000-01-01")
    assert response.status_code == 200
    data = response.json()
    assert data["gainers"] == []
    assert data["losers"] == []


# ── GET /stocks/{symbol} ─────────────────────────────────────────────────────


def test_stock_detail_found(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/SNTS")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SNTS"
    assert data["name"] == "SONATEL SN"
    assert data["sector"] == "Télécommunications"
    assert data["country"] == "SN"


def test_stock_detail_has_latest_price(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/SNTS")
    data = response.json()
    price = data["latest_price"]
    assert price is not None
    assert float(price["close_price"]) == pytest.approx(28800.0)
    assert price["trading_date"] == str(TRADING_DATE)


def test_stock_detail_has_latest_dividend(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/SNTS")
    data = response.json()
    div = data["latest_dividend"]
    assert div is not None
    assert div["fiscal_year"] == 2025
    assert float(div["net_amount"]) == pytest.approx(1655.0)


def test_stock_detail_no_dividend(client: TestClient) -> None:
    """NTLC has no dividend in seeded data — field should be null."""
    response = client.get("/api/v1/stocks/NTLC")
    assert response.status_code == 200
    assert response.json()["latest_dividend"] is None


def test_stock_detail_case_insensitive(client: TestClient) -> None:
    """Symbols are normalised to uppercase in the route."""
    response = client.get("/api/v1/stocks/snts")
    assert response.status_code == 200
    assert response.json()["symbol"] == "SNTS"


def test_stock_detail_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/XXXXXX")
    assert response.status_code == 404
    assert "XXXXXX" in response.json()["detail"]


# ── GET /stocks/{symbol}/prices ───────────────────────────────────────────────


def test_stock_prices_returns_list(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/SNTS/prices")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1  # one seeded price row
    assert data[0]["trading_date"] == str(TRADING_DATE)


def test_stock_prices_ohlcv_fields(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/SNTS/prices")
    row = response.json()[0]
    assert float(row["close_price"]) == pytest.approx(28800.0)
    assert float(row["open_price"]) == pytest.approx(28850.0)
    assert float(row["high_price"]) == pytest.approx(29000.0)
    assert float(row["low_price"]) == pytest.approx(28700.0)
    assert row["volume"] == 14844
    assert float(row["variation_pct"]) == pytest.approx(-0.35)


def test_stock_prices_days_param_filters(client: TestClient) -> None:
    """days=1 should still include TRADING_DATE (it's the latest date)."""
    response = client.get("/api/v1/stocks/SNTS/prices?days=1")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_stock_prices_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/XXXXXX/prices")
    assert response.status_code == 404


def test_stock_prices_days_max_validation(client: TestClient) -> None:
    """days > 365 should be rejected with 422."""
    response = client.get("/api/v1/stocks/SNTS/prices?days=366")
    assert response.status_code == 422


# ── GET /stocks/{symbol}/dividends (Premium) ──────────────────────────────────


def test_dividends_returns_list(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/SNTS/dividends")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["fiscal_year"] == 2025
    assert float(data[0]["net_amount"]) == pytest.approx(1655.0)
    assert data[0]["is_confirmed"] is True


def test_dividends_empty_when_none(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/NTLC/dividends")
    assert response.status_code == 200
    assert response.json() == []


def test_dividends_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/XXXXXX/dividends")
    assert response.status_code == 404


# ── GET /stocks/{symbol}/financials (Premium) ─────────────────────────────────


def test_financials_returns_list(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/SNTS/financials")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    row = data[0]
    assert row["fiscal_year"] == 2024
    assert row["revenue"] == 450_000_000
    assert row["net_income"] == 80_000_000
    assert row["total_debt"] == 50_000_000
    assert row["equity"] == 300_000_000


def test_financials_empty_when_none(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/NTLC/financials")
    assert response.status_code == 200
    assert response.json() == []


def test_financials_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/XXXXXX/financials")
    assert response.status_code == 404


# ── Smoke test — route registration ───────────────────────────────────────────


def test_router_paths_registered() -> None:
    """Ensure all expected paths are present in the router."""
    from app.api.routes.stocks import router

    paths = {r.path for r in router.routes}
    assert "/stocks/" in paths
    assert "/stocks/summary" in paths
    assert "/stocks/search" in paths
    assert "/stocks/top-movers" in paths
    assert "/stocks/{symbol}" in paths
    assert "/stocks/{symbol}/prices" in paths
    assert "/stocks/{symbol}/dividends" in paths
    assert "/stocks/{symbol}/financials" in paths
