"""Custom exceptions for Akwaba Invest backend."""
from typing import Any


class AkwabaException(Exception):
    """Base exception for all Akwaba Invest errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class StockNotFoundError(AkwabaException):
    """Raised when a stock symbol does not exist in the database."""

    def __init__(self, symbol: str) -> None:
        super().__init__(f"Stock '{symbol}' not found", status_code=404)


class FirebaseInitError(AkwabaException):
    """Raised when Firebase fails to initialise."""

    def __init__(self) -> None:
        super().__init__("Firebase initialisation failed", status_code=500)


class UnauthorizedError(AkwabaException):
    """Raised when the caller lacks a valid Firebase token."""

    def __init__(self) -> None:
        super().__init__("Authentication required", status_code=401)


class PremiumRequiredError(AkwabaException):
    """Raised when a premium subscription is required."""

    def __init__(self) -> None:
        super().__init__("Premium subscription required", status_code=403)


class BocDownloadError(AkwabaException):
    """Raised when the BOC PDF cannot be downloaded."""

    def __init__(self, target_date: Any) -> None:
        super().__init__(
            f"BOC PDF not available for {target_date}. "
            "Market may be closed or PDF not yet published.",
            status_code=503,
        )


class BocParseError(AkwabaException):
    """Raised when the BOC PDF cannot be parsed."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"BOC parse failed: {reason}", status_code=500)


class NoDataError(AkwabaException):
    """Raised when no stock data was extracted from a BOC."""

    def __init__(self) -> None:
        super().__init__("No stock data found in BOC", status_code=404)


class InsufficientSharesError(AkwabaException):
    """Raised when the user tries to sell more shares than they own."""

    def __init__(self, symbol: str, needed: float, available: float) -> None:
        super().__init__(
            f"Actions insuffisantes pour {symbol}. "
            f"Vous avez {available} action(s), tentative de vendre {needed}.",
            status_code=400,
        )


class PositionNotFoundError(AkwabaException):
    """Raised when a portfolio position does not exist."""

    def __init__(self, symbol: str) -> None:
        super().__init__(
            f"Aucune position trouvée pour {symbol}",
            status_code=404,
        )
