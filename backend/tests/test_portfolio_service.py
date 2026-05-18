import pytest
from decimal import Decimal

from app.services.portfolio_service import compute_consolidated_pru


def test_pru_first_purchase() -> None:
    # First purchase: PRU = purchase price
    result = compute_consolidated_pru(
        old_qty=0, old_pru=Decimal("0"), new_qty=10, purchase_price=Decimal("1000")
    )
    assert result == Decimal("1000")


def test_pru_averaging_down() -> None:
    # Buy 10 @ 1000 then 10 @ 800 → PRU = 900
    result = compute_consolidated_pru(
        old_qty=10, old_pru=Decimal("1000"), new_qty=10, purchase_price=Decimal("800")
    )
    assert result == Decimal("900")


def test_pru_averaging_up() -> None:
    # Buy 10 @ 1000 then 5 @ 1200 → PRU = 1066.67
    result = compute_consolidated_pru(
        old_qty=10, old_pru=Decimal("1000"), new_qty=5, purchase_price=Decimal("1200")
    )
    expected = (Decimal("10") * Decimal("1000") + Decimal("5") * Decimal("1200")) / Decimal("15")
    assert result == expected
