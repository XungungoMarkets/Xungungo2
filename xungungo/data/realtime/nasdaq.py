from __future__ import annotations
import json
import random
import urllib.request
from datetime import datetime
from urllib.error import HTTPError

from xungungo.core.logger import get_logger
from xungungo.data.realtime.base import RealtimeDataSource, RealtimeQuote

# User-Agent rotation pool (various browsers/platforms)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


class NasdaqRealtimeSource(RealtimeDataSource):
    """Realtime data source using NASDAQ API. Supports US stocks."""

    API_URL = "https://api.nasdaq.com/api/quote/{symbol}/info?assetclass=stocks"

    def __init__(self):
        self.log = get_logger("xungungo.realtime.nasdaq")

    @property
    def name(self) -> str:
        return "NASDAQ"

    @property
    def supported_exchanges(self) -> list[str]:
        return ["NASDAQ", "NYSE", "AMEX", "BATS", "ARCA"]

    def supports_symbol(self, symbol: str) -> bool:
        """
        Check if symbol is likely a US stock.
        Simple heuristic: no dots or colons (not forex, not international).
        """
        symbol = symbol.upper().strip()
        # US stocks typically don't have special characters
        if "." in symbol or ":" in symbol or "-" in symbol:
            # Exceptions: BRK.A, BRK.B are valid
            if not symbol.startswith("BRK."):
                return False
        # Crypto pairs end with -USD
        if symbol.endswith("-USD"):
            return False
        return True

    def get_headers(self) -> dict:
        """Get browser-like headers with User-Agent rotation."""
        user_agent = random.choice(USER_AGENTS)
        return {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.nasdaq.com",
            "Referer": "https://www.nasdaq.com/",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
        }

    def fetch_quote(self, symbol: str) -> RealtimeQuote:
        """Fetch realtime quote from NASDAQ API."""
        symbol = symbol.upper().strip()

        if not self.supports_symbol(symbol):
            raise ValueError(f"Symbol {symbol} not supported by NASDAQ source")

        url = self.API_URL.format(symbol=symbol)
        self.log.debug(f"Fetching quote for {symbol}")

        req = urllib.request.Request(url, headers=self.get_headers())

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
        except HTTPError as e:
            if e.code == 429:
                raise ConnectionError(f"Rate limited (429) for {symbol}")
            elif e.code == 403:
                raise ConnectionError(f"Access denied (403) for {symbol}")
            else:
                raise ConnectionError(f"HTTP {e.code} for {symbol}: {e.reason}")

        # Check API response status
        status = data.get("status", {})
        if status.get("rCode") != 200:
            error_msg = status.get("bCodeMessage", ["Unknown error"])
            raise ValueError(f"NASDAQ API error for {symbol}: {error_msg}")

        quote_data = data.get("data", {})
        primary_data = quote_data.get("primaryData", {})

        # Parse price
        price_str = primary_data.get("lastSalePrice", "$0")
        price = self._parse_price(price_str)

        # Parse change
        change_str = primary_data.get("netChange", "0")
        change = self._parse_price(change_str)

        # Parse percent
        percent_str = primary_data.get("percentageChange", "0%")
        change_percent = self._parse_percent(percent_str)

        return RealtimeQuote(
            symbol=symbol,
            price=price,
            change=change,
            change_percent=change_percent,
            volume=self._parse_volume(primary_data.get("volume", "")),
            timestamp=datetime.now(),
            company_name=quote_data.get("companyName", symbol),
            exchange=quote_data.get("exchange", ""),
            market_status=quote_data.get("marketStatus", ""),
            # Keep original formatted strings
            price_str=price_str,
            change_str=change_str,
            change_percent_str=percent_str,
            timestamp_str=primary_data.get("lastTradeTimestamp", ""),
        )

    def _parse_price(self, value: str) -> float:
        """Parse price string like '$123.45' or '+$1.23' to float."""
        if not value:
            return 0.0
        cleaned = value.replace("$", "").replace(",", "").replace("+", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _parse_percent(self, value: str) -> float:
        """Parse percent string like '+1.23%' to float."""
        if not value:
            return 0.0
        cleaned = value.replace("%", "").replace("+", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _parse_volume(self, value: str) -> int | None:
        """Parse volume string like '1,234,567' to int."""
        if not value:
            return None
        cleaned = value.replace(",", "").strip()
        try:
            return int(cleaned)
        except ValueError:
            return None
