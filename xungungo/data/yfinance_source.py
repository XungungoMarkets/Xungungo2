from __future__ import annotations
from collections import OrderedDict
import threading
import time
import pandas as pd
import yfinance as yf

from xungungo.core.logger import get_logger
from .datasource_base import DataSource
from .normalize import normalize_yfinance

# Global lock for yfinance - it's not thread-safe for concurrent downloads
_yfinance_lock = threading.Lock()


class YFinanceDataSource(DataSource):
    """
    DataSource implementation using yfinance.
    Includes in-memory cache with 1-day TTL and retry logic for network failures.

    Note: yfinance is NOT thread-safe for concurrent downloads. This class uses
    a global lock to serialize calls to yf.download().
    """
    # Cache TTL in seconds (1 day)
    CACHE_TTL = 86400

    # Cache size limit (LRU eviction when exceeded)
    # Limits memory usage to ~100 DataFrames max
    MAX_CACHE_SIZE = 100

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
        "1d": "max",
        "1wk": "max",
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

    # Interval order from smallest to largest granularity
    _INTERVAL_ORDER = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk"]

    def __init__(self):
        self.log = get_logger("xungungo.yfinance")
        self._cache: OrderedDict[str, tuple] = OrderedDict()  # {cache_key: (dataframe, timestamp)}

    def normalize_interval_period(self, interval: str, period: str) -> tuple[str, str]:
        """Clamp period down if it exceeds the interval's maximum."""
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

    def get_min_interval_for_period(self, period: str) -> str:
        """
        Get the minimum (finest granularity) interval that supports the given period.

        For example:
        - period "10y" → returns "1d" (smallest interval that supports 10y)
        - period "2y" → returns "1h" (smallest interval that supports 2y)
        - period "1mo" → returns "5m" (smallest interval that supports 1mo)
        - period "5d" → returns "1m" (smallest interval that supports 5d)
        """
        period = (period or "").strip()
        try:
            period_idx = self._PERIOD_ORDER.index(period)
        except ValueError:
            return "1d"  # Default fallback

        # Find the smallest interval that can support this period
        for interval in self._INTERVAL_ORDER:
            max_period = self._MAX_PERIOD_BY_INTERVAL.get(interval)
            if not max_period:
                continue
            try:
                max_idx = self._PERIOD_ORDER.index(max_period)
                if max_idx >= period_idx:
                    return interval
            except ValueError:
                continue

        return "1d"  # Fallback to daily

    def normalize_period_adjusting_interval(self, interval: str, period: str) -> tuple[str, str]:
        """
        Adjust interval UP if the period requires a larger interval.
        Used when user changes period and expects interval to adapt.
        """
        interval = (interval or "").strip()
        period = (period or "").strip()

        # Check if current interval supports the period
        max_period = self._MAX_PERIOD_BY_INTERVAL.get(interval)
        if not max_period:
            return interval, period

        try:
            max_idx = self._PERIOD_ORDER.index(max_period)
            period_idx = self._PERIOD_ORDER.index(period)
        except ValueError:
            return interval, period

        if period_idx > max_idx:
            # Period is too large for current interval, find minimum interval
            new_interval = self.get_min_interval_for_period(period)
            self.log.info(
                f"Adjusting interval from '{interval}' to '{new_interval}' for period '{period}'"
            )
            return new_interval, period

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
                # Move to end (mark as recently used)
                self._cache.move_to_end(cache_key)
                return df.copy()
            else:
                self.log.info(f"Cache expired for {symbol} (age: {age:.0f}s)")
                del self._cache[cache_key]

        # Fetch with retry logic
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                self.log.info(f"Fetching {symbol} (attempt {attempt + 1}/{self.MAX_RETRIES})")

                # CRITICAL: yfinance is NOT thread-safe - must serialize downloads
                with _yfinance_lock:
                    df = yf.download(
                        symbol,
                        period=period,
                        interval=interval,
                        auto_adjust=False,
                        progress=False
                    )

                if df is None or df.empty:
                    raise ValueError(f"No data returned for symbol: {symbol}")

                # Normalize and cache with LRU eviction
                normalized = normalize_yfinance(df)

                # Evict oldest entries if cache exceeds limit
                while len(self._cache) >= self.MAX_CACHE_SIZE:
                    oldest_key = next(iter(self._cache))
                    self.log.debug(f"Evicting cache entry: {oldest_key}")
                    del self._cache[oldest_key]

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
