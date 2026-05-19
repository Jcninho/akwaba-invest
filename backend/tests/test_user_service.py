from datetime import date, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.models import Subscription, User
from app.services.user_service import get_active_subscription_end_date, upsert_user


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_upsert_user_creates_new(session):
    user = upsert_user(session, firebase_uid="abc123", email="test@example.com")
    assert user.id is not None
    assert user.firebase_uid == "abc123"
    assert user.plan == "free"


def test_upsert_user_idempotent(session):
    u1 = upsert_user(session, firebase_uid="abc123", email="test@example.com")
    u2 = upsert_user(session, firebase_uid="abc123", email="test@example.com")
    assert u1.id == u2.id


def test_get_active_subscription_end_date_none(session):
    user = upsert_user(session, firebase_uid="abc123", email="test@example.com")
    result = get_active_subscription_end_date(session, user.id)
    assert result is None


def test_get_active_subscription_end_date_active(session):
    user = upsert_user(session, firebase_uid="abc123", email="test@example.com")
    sub = Subscription(
        user_id=user.id,
        plan_type="monthly",
        amount_fcfa=2000,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status="active",
    )
    session.add(sub)
    session.commit()
    result = get_active_subscription_end_date(session, user.id)
    assert result is not None


def test_get_active_subscription_end_date_expired(session):
    user = upsert_user(session, firebase_uid="abc123", email="test@example.com")
    sub = Subscription(
        user_id=user.id,
        plan_type="monthly",
        amount_fcfa=2000,
        start_date=date.today() - timedelta(days=60),
        end_date=date.today() - timedelta(days=30),
        status="active",
    )
    session.add(sub)
    session.commit()
    result = get_active_subscription_end_date(session, user.id)
    assert result is None
