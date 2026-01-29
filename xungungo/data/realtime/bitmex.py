from __future__ import annotations
import json
import urllib.request
from datetime import datetime
from urllib.error import HTTPError

from xungungo.core.logger import get_logger
from xungungo.data.realtime.base import RealtimeDataSource, RealtimeQuote


# Mapping from common crypto symbols to BitMEX instrument symbols
SYMBOL_MAP = {
    # Bitcoin
    "BTC": "XBTUSD",
    "BTC-USD": "XBTUSD",
    "BTCUSD": "XBTUSD",
    "XBT": "XBTUSD",
    # Ethereum
    "ETH": "ETHUSD",
    "ETH-USD": "ETHUSD",
    "ETHUSD": "ETHUSD",
    # Solana
    "SOL": "SOLUSD",
    "SOL-USD": "SOLUSD",
    "SOLUSD": "SOLUSD",
    # XRP
    "XRP": "XRPUSD",
    "XRP-USD": "XRPUSD",
    "XRPUSD": "XRPUSD",
    # Dogecoin
    "DOGE": "DOGEUSD",
    "DOGE-USD": "DOGEUSD",
    "DOGEUSD": "DOGEUSD",
    # Litecoin
    "LTC": "LTCUSD",
    "LTC-USD": "LTCUSD",
    "LTCUSD": "LTCUSD",
    # Cardano
    "ADA": "ADAUSD",
    "ADA-USD": "ADAUSD",
    "ADAUSD": "ADAUSD",
    # Avalanche
    "AVAX": "AVAXUSD",
    "AVAX-USD": "AVAXUSD",
    "AVAXUSD": "AVAXUSD",
    # Chainlink
    "LINK": "LINKUSD",
    "LINK-USD": "LINKUSD",
    "LINKUSD": "LINKUSD",
    # Polkadot
    "DOT": "DOTUSD",
    "DOT-USD": "DOTUSD",
    "DOTUSD": "DOTUSD",
}

# Common cryptocurrency symbols (for detection)
CRYPTO_SYMBOLS = {
    "BTC", "ETH", "SOL", "XRP", "DOGE", "LTC", "ADA", "AVAX", "LINK", "DOT",
    "MATIC", "SHIB", "UNI", "ATOM", "XLM", "ALGO", "FIL", "NEAR", "APT", "ARB",
}


class BitMEXRealtimeSource(RealtimeDataSource):
    """Realtime data source using BitMEX public API. Supports cryptocurrencies."""

    API_URL = "https://www.bitmex.com/api/v1/instrument"

    def __init__(self):
        self.log = get_logger("xungungo.realtime.bitmex")
        self._active_instruments: set[str] | None = None

    @property
    def name(self) -> str:
        return "BitMEX"

    @property
    def supported_exchanges(self) -> list[str]:
        return ["CRYPTO", "BITMEX"]

    def supports_symbol(self, symbol: str) -> bool:
        """Check if symbol is a cryptocurrency we can handle."""
        symbol = symbol.upper().strip()

        # Direct match in our mapping
        if symbol in SYMBOL_MAP:
            return True

        # Check if it's a known crypto symbol
        base_symbol = symbol.replace("-USD", "").replace("USD", "")
        if base_symbol in CRYPTO_SYMBOLS:
            return True

        # Check for -USD suffix (crypto convention from Yahoo)
        if symbol.endswith("-USD"):
            return True

        return False

    def _get_bitmex_symbol(self, symbol: str) -> str:
        """Convert user symbol to BitMEX instrument symbol."""
        symbol = symbol.upper().strip()

        # Direct mapping
        if symbol in SYMBOL_MAP:
            return SYMBOL_MAP[symbol]

        # Try to construct: BTC-USD -> BTCUSD, ETH -> ETHUSD
        base = symbol.replace("-USD", "").replace("-", "")
        if not base.endswith("USD"):
            base = base + "USD"

        # Special case: BTC -> XBT
        if base == "BTCUSD":
            return "XBTUSD"

        return base

    def get_headers(self) -> dict:
        """Get headers for BitMEX API."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }

    def fetch_quote(self, symbol: str) -> RealtimeQuote:
        """Fetch realtime quote from BitMEX API."""
        original_symbol = symbol.upper().strip()

        if not self.supports_symbol(original_symbol):
            raise ValueError(f"Symbol {original_symbol} not supported by BitMEX source")

        bitmex_symbol = self._get_bitmex_symbol(original_symbol)
        self.log.debug(f"Fetching {original_symbol} as {bitmex_symbol} from BitMEX")

        # Build URL with query params
        url = f"{self.API_URL}?symbol={bitmex_symbol}&columns=symbol,lastPrice,lastChangePcnt,volume24h,prevClosePrice,underlying"

        req = urllib.request.Request(url, headers=self.get_headers())

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
        except HTTPError as e:
            if e.code == 429:
                raise ConnectionError(f"Rate limited (429) for {bitmex_symbol}")
            elif e.code == 404:
                raise ValueError(f"Symbol {bitmex_symbol} not found on BitMEX")
            else:
                raise ConnectionError(f"HTTP {e.code} for {bitmex_symbol}: {e.reason}")

        if not data:
            raise ValueError(f"No data returned for {bitmex_symbol}")

        # API returns a list, get first item
        instrument = data[0] if isinstance(data, list) else data

        # Extract price data
        last_price = instrument.get("lastPrice", 0) or 0
        prev_close = instrument.get("prevClosePrice", last_price) or last_price
        change = last_price - prev_close
        change_pct = (instrument.get("lastChangePcnt", 0) or 0) * 100  # API returns decimal

        volume = instrument.get("volume24h")
        if volume:
            volume = int(volume)

        return RealtimeQuote(
            symbol=original_symbol,
            price=float(last_price),
            change=float(change),
            change_percent=float(change_pct),
            volume=volume,
            timestamp=datetime.now(),
            company_name=self._get_crypto_name(original_symbol),
            exchange="BitMEX",
            market_status="open",  # Crypto markets are 24/7
            price_str=f"${last_price:,.2f}",
            change_str=f"{'+' if change >= 0 else ''}{change:,.2f}",
            change_percent_str=f"{'+' if change_pct >= 0 else ''}{change_pct:.2f}%",
            timestamp_str=datetime.now().strftime("%H:%M:%S"),
        )

    def _get_crypto_name(self, symbol: str) -> str:
        """Get friendly name for cryptocurrency."""
        names = {
            "BTC": "Bitcoin",
            "ETH": "Ethereum",
            "SOL": "Solana",
            "XRP": "Ripple",
            "DOGE": "Dogecoin",
            "LTC": "Litecoin",
            "ADA": "Cardano",
            "AVAX": "Avalanche",
            "LINK": "Chainlink",
            "DOT": "Polkadot",
            "MATIC": "Polygon",
            "SHIB": "Shiba Inu",
            "UNI": "Uniswap",
            "ATOM": "Cosmos",
            "XLM": "Stellar",
        }
        base = symbol.upper().replace("-USD", "").replace("USD", "")
        return names.get(base, symbol)
