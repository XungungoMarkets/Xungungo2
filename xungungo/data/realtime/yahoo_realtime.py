from __future__ import annotations
from datetime import datetime

import yfinance as yf

from xungungo.core.logger import get_logger
from xungungo.data.realtime.base import RealtimeDataSource, RealtimeQuote


class YahooRealtimeSource(RealtimeDataSource):
    """
    Realtime data source using Yahoo Finance (yfinance).

    Note: Yahoo data may have 15-minute delay for some markets.
    This source is used as a fallback for non-US stocks and crypto.
    """

    def __init__(self):
        self.log = get_logger("xungungo.realtime.yahoo")

    @property
    def name(self) -> str:
        return "Yahoo Finance"

    @property
    def supported_exchanges(self) -> list[str]:
        # Yahoo supports almost everything
        return ["*"]  # Wildcard for all exchanges

    def supports_symbol(self, symbol: str) -> bool:
        """Yahoo supports almost any symbol."""
        return bool(symbol and symbol.strip())

    def fetch_quote(self, symbol: str) -> RealtimeQuote:
        """Fetch quote using yfinance."""
        symbol = symbol.upper().strip()
        self.log.debug(f"Fetching Yahoo quote for {symbol}")

        try:
            # Create fresh ticker object each time to avoid stale cached data
            ticker = yf.Ticker(symbol)

            # Get fast info
            info = ticker.fast_info

            price = float(info.last_price) if info.last_price else 0.0
            prev_close = float(info.previous_close) if info.previous_close else price

            change = price - prev_close
            change_percent = (change / prev_close * 100) if prev_close else 0.0

            # Try to get more info (may be slower)
            full_info = self._get_full_info(ticker)

            return RealtimeQuote(
                symbol=symbol,
                price=price,
                change=change,
                change_percent=change_percent,
                volume=int(info.last_volume) if info.last_volume else None,
                timestamp=datetime.now(),
                company_name=full_info.get("shortName") or full_info.get("longName") or symbol,
                exchange=full_info.get("exchange", ""),
                market_status=self._get_market_status(full_info),
                price_str=f"${price:.2f}" if price else "-",
                change_str=f"{'+' if change >= 0 else ''}{change:.2f}",
                change_percent_str=f"{'+' if change_percent >= 0 else ''}{change_percent:.2f}%",
                timestamp_str=datetime.now().strftime("%b %d, %Y %I:%M %p"),
            )

        except Exception as e:
            self.log.error(f"Yahoo fetch error for {symbol}: {e}")
            raise ConnectionError(f"Failed to fetch {symbol} from Yahoo: {e}")

    def _get_full_info(self, ticker: yf.Ticker) -> dict:
        """Get full ticker info, with error handling."""
        try:
            return ticker.info or {}
        except Exception:
            return {}

    def _get_market_status(self, info: dict) -> str:
        """Determine market status from ticker info."""
        market_state = info.get("marketState", "").upper()

        if market_state == "REGULAR":
            return "Market Open"
        elif market_state == "PRE":
            return "Pre-Market"
        elif market_state == "POST":
            return "After Hours"
        elif market_state == "CLOSED":
            return "Market Closed"
        else:
            return ""

