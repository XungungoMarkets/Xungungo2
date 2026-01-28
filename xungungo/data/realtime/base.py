from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RealtimeQuote:
    """Standardized realtime quote data."""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None
    company_name: Optional[str] = None
    exchange: Optional[str] = None
    market_status: Optional[str] = None  # "open", "closed", "pre", "post"

    # For display formatting
    price_str: Optional[str] = None
    change_str: Optional[str] = None
    change_percent_str: Optional[str] = None
    timestamp_str: Optional[str] = None

    @property
    def is_positive(self) -> bool:
        return self.change >= 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "lastSalePrice": self.price_str or f"${self.price:.2f}",
            "netChange": self.change_str or f"{'+' if self.change >= 0 else ''}{self.change:.2f}",
            "percentageChange": self.change_percent_str or f"{'+' if self.change_percent >= 0 else ''}{self.change_percent:.2f}%",
            "volume": str(self.volume) if self.volume else "",
            "lastTradeTimestamp": self.timestamp_str or (self.timestamp.isoformat() if self.timestamp else ""),
            "companyName": self.company_name or self.symbol,
            "exchange": self.exchange or "",
            "marketStatus": self.market_status or "",
            "deltaIndicator": "up" if self.is_positive else "down",
            "timestamp": datetime.now().isoformat(),
        }


class RealtimeDataSource(ABC):
    """Abstract base class for realtime data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass

    @property
    @abstractmethod
    def supported_exchanges(self) -> list[str]:
        """List of supported exchange codes (e.g., ['NASDAQ', 'NYSE', 'AMEX'])."""
        pass

    @abstractmethod
    def supports_symbol(self, symbol: str) -> bool:
        """Check if this source can provide data for the given symbol."""
        pass

    @abstractmethod
    def fetch_quote(self, symbol: str) -> RealtimeQuote:
        """
        Fetch realtime quote for a symbol.

        Args:
            symbol: The ticker symbol

        Returns:
            RealtimeQuote with current data

        Raises:
            ValueError: If symbol is invalid or not supported
            ConnectionError: If API request fails
        """
        pass

    def get_headers(self) -> dict:
        """Get HTTP headers for API requests. Override if needed."""
        return {}
