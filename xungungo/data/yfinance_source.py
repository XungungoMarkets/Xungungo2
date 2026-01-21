from __future__ import annotations
import time
import pandas as pd
import yfinance as yf

from xungungo.core.logger import get_logger
from .datasource_base import DataSource
from .normalize import normalize_yfinance


class YFinanceDataSource(DataSource):
    """
    DataSource implementation using yfinance.
    Includes in-memory cache with 1-day TTL and retry logic for network failures.
    """
    # Cache TTL in seconds (1 day)
    CACHE_TTL = 86400

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # Initial delay in seconds

    # Max supported period per interval (based on yfinance/Yahoo limits)
    _MAX_PERIOD_BY_INTERVAL = {
        "1m": "5d",
        "5m": "1mo",
        "15m": "1mo",
        "30m": "1mo",
        "1h": "2y",
        "1d": "10y",
        "1wk": "10y",
    }

    _PERIOD_ORDER = [
        "1d",
        "5d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max",
    ]

    def __init__(self):
        self.log = get_logger("xungungo.yfinance")
        self._cache = {}  # Format: {cache_key: (dataframe, timestamp)}

    def normalize_interval_period(self, interval: str, period: str) -> tuple[str, str]:
        interval = (interval or "").strip()
        period = (period or "").strip()
        max_period = self._MAX_PERIOD_BY_INTERVAL.get(interval)
        if not max_period:
            return interval, period
        try:
            max_idx = self._PERIOD_ORDER.index(max_period)
            period_idx = self._PERIOD_ORDER.index(period)
        except ValueError:
            return interval, period
        if period_idx > max_idx:
            self.log.info(
                f"Clamping period '{period}' to '{max_period}' for interval '{interval}'"
            )
            return interval, max_period
        return interval, period

    def fetch_ohlcv(self, symbol: str, interval: str = "1d", period: str = "10y") -> pd.DataFrame:
        """
        Fetch OHLCV data with caching and retry logic.

        Args:
            symbol: Ticker symbol (e.g., "AAPL", "BTC-USD")
            interval: Data interval (e.g., "1d", "1h")
            period: Historical period (e.g., "10y", "1y")

        Returns:
            Normalized DataFrame with OHLCV data

        Raises:
            ValueError: If no data is available after retries
        """
        interval, period = self.normalize_interval_period(interval, period)
        cache_key = f"{symbol}:{interval}:{period}"

        # Check cache
        if cache_key in self._cache:
            df, timestamp = self._cache[cache_key]
            age = time.time() - timestamp

            if age < self.CACHE_TTL:
                self.log.info(f"Cache hit for {symbol} (age: {age:.0f}s)")
                return df.copy()
            else:
                self.log.info(f"Cache expired for {symbol} (age: {age:.0f}s)")
                del self._cache[cache_key]

        # Fetch with retry logic
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                self.log.info(f"Fetching {symbol} (attempt {attempt + 1}/{self.MAX_RETRIES})")

                df = yf.download(
                    symbol,
                    period=period,
                    interval=interval,
                    auto_adjust=False,
                    progress=False
                )

                if df is None or df.empty:
                    raise ValueError(f"No data returned for symbol: {symbol}")

                # Normalize and cache
                normalized = normalize_yfinance(df)
                self._cache[cache_key] = (normalized.copy(), time.time())

                self.log.info(f"Successfully fetched {len(normalized)} rows for {symbol}")
                return normalized

            except Exception as e:
                last_error = e
                self.log.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")

                if attempt < self.MAX_RETRIES - 1:
                    # Exponential backoff
                    delay = self.RETRY_DELAY * (2 ** attempt)
                    self.log.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)

        # All retries failed
        error_msg = f"Failed to fetch data for {symbol} after {self.MAX_RETRIES} attempts: {last_error}"
        self.log.error(error_msg)
        raise ValueError(error_msg)

    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        self.log.info("Cache cleared")
