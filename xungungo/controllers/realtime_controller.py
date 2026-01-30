from __future__ import annotations
from collections import OrderedDict
import json
import random
import threading
import time
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot, QTimer, QMetaObject, Qt, Q_ARG

from xungungo.core.logger import get_logger
from xungungo.data.realtime import (
    RealtimeDataSource,
    RealtimeQuote,
    NasdaqRealtimeSource,
    YahooRealtimeSource,
    BitMEXRealtimeSource,
)


class RealtimeController(QObject):
    """Controller for real-time quote data polling with multiple data sources."""

    # Signal: (tabId, jsonData) - emitted when new quote data is available
    realtimeDataReady = Signal(str, str)
    # Signal: (tabId, errorMessage) - emitted on API error
    realtimeError = Signal(str, str)
    # Signal: (tabId, isPolling) - emitted when polling state changes
    pollingChanged = Signal(str, bool)
    # Signal: (symbol, price, timestamp) - for chart updates
    priceUpdate = Signal(str, float, int)

    # Polling settings
    BASE_POLL_INTERVAL_MS = 15000  # 15 seconds base interval
    JITTER_MS = 3000  # ±3 seconds random jitter
    MIN_REQUEST_DELAY_MS = 500  # Minimum delay between symbol requests

    # Backoff settings
    MAX_BACKOFF_MS = 300000  # 5 minutes max backoff
    BACKOFF_MULTIPLIER = 2.0

    # Cache size limits (LRU eviction when exceeded)
    MAX_CACHE_SIZE = 200  # Max symbols in cache

    def __init__(self):
        super().__init__()
        self.log = get_logger("xungungo.realtime")

        # Data sources (in priority order)
        self._sources: list[RealtimeDataSource] = [
            BitMEXRealtimeSource(),  # Crypto first (specific)
            NasdaqRealtimeSource(),  # US stocks
            YahooRealtimeSource(),   # Fallback for everything else
        ]

        # Per-tab polling state
        self._polling_tabs: dict[str, bool] = {}
        self._cached_data: OrderedDict[str, dict] = OrderedDict()  # symbol -> last known data (LRU)
        self._current_symbols: dict[str, str] = {}  # tabId -> symbol
        self._symbol_sources: OrderedDict[str, str] = OrderedDict()  # symbol -> source name (LRU)

        # Rate limiting and backoff state
        self._consecutive_errors: int = 0
        self._current_backoff_ms: int = 0
        self._last_request_time: float = 0
        self._rate_limited_until: float = 0  # Unix timestamp

        # Single timer for all tabs (singleShot for variable intervals)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._poll_all_active)

        # Track running fetch threads
        self._fetch_lock = threading.Lock()
        self._fetching: set[str] = set()  # symbols currently being fetched

        self.log.info(f"RealtimeController initialized with {len(self._sources)} sources")

    @Slot(str, str)
    def startPolling(self, tabId: str, symbol: str):
        """Start polling for a specific tab/symbol."""
        if not symbol:
            return

        symbol = symbol.upper().strip()
        old_symbol = self._current_symbols.get(tabId)

        # If same symbol already polling, just return
        if old_symbol == symbol and self._polling_tabs.get(tabId, False):
            self.log.debug(f"Already polling {symbol} for tab {tabId}")
            return

        self._current_symbols[tabId] = symbol
        self._polling_tabs[tabId] = True
        self.pollingChanged.emit(tabId, True)

        # Emit cached data immediately if available
        if symbol in self._cached_data:
            self.log.debug(f"Emitting cached data for {symbol}")
            self.realtimeDataReady.emit(tabId, json.dumps(self._cached_data[symbol]))

        # Fetch immediately (unless rate limited)
        if time.time() < self._rate_limited_until:
            wait_secs = int(self._rate_limited_until - time.time())
            self.log.warning(f"Rate limited, waiting {wait_secs}s before fetching")
        else:
            self._fetch_quote(tabId, symbol)

        # Schedule next poll with jitter
        self._schedule_next_poll()

        self.log.info(f"Started polling for tab {tabId}, symbol {symbol}")

    @Slot(str)
    def stopPolling(self, tabId: str):
        """Stop polling for a specific tab."""
        was_polling = self._polling_tabs.get(tabId, False)
        self._polling_tabs[tabId] = False
        self._current_symbols.pop(tabId, None)

        if was_polling:
            self.pollingChanged.emit(tabId, False)
            self.log.info(f"Stopped polling for tab {tabId}")

        # Stop timer if no tabs are polling
        if not any(self._polling_tabs.values()):
            self._timer.stop()
            self.log.debug("Stopped polling timer (no active tabs)")

    @Slot(str, result=str)
    def getCachedData(self, symbol: str) -> str:
        """Get cached quote data for a symbol."""
        symbol = symbol.upper().strip()
        if symbol in self._cached_data:
            return json.dumps(self._cached_data[symbol])
        return ""

    @Slot(str, result=bool)
    def isPolling(self, tabId: str) -> bool:
        """Check if a tab is currently polling."""
        return self._polling_tabs.get(tabId, False)

    def _schedule_next_poll(self):
        """Schedule next poll with jitter."""
        if not any(self._polling_tabs.values()):
            return  # No active tabs

        interval = self._get_next_interval()
        self._timer.start(interval)
        self.log.debug(f"Next poll scheduled in {interval}ms")

    def _get_next_interval(self) -> int:
        """Calculate next poll interval with jitter and backoff."""
        base = self.BASE_POLL_INTERVAL_MS

        # Apply backoff if we have consecutive errors
        if self._current_backoff_ms > 0:
            base = self._current_backoff_ms

        # Add random jitter (-JITTER to +JITTER)
        jitter = random.randint(-self.JITTER_MS, self.JITTER_MS)
        interval = max(1000, base + jitter)  # Minimum 1 second

        return interval

    def _poll_all_active(self):
        """Poll all active tabs (called by timer)."""
        # Check if rate limited
        if time.time() < self._rate_limited_until:
            wait_ms = int((self._rate_limited_until - time.time()) * 1000)
            self.log.warning(f"Still rate limited, waiting {wait_ms}ms")
            self._timer.start(wait_ms + 1000)  # Re-check after limit expires
            return

        # Get unique symbols to fetch (avoid duplicate requests)
        symbols_to_fetch: dict[str, list[str]] = {}  # symbol -> [tabIds]
        for tabId, is_polling in list(self._polling_tabs.items()):
            if is_polling and tabId in self._current_symbols:
                symbol = self._current_symbols[tabId]
                if symbol not in symbols_to_fetch:
                    symbols_to_fetch[symbol] = []
                symbols_to_fetch[symbol].append(tabId)

        # Fetch each symbol with delay between requests
        for idx, (symbol, tab_ids) in enumerate(symbols_to_fetch.items()):
            # Add delay between symbols to avoid burst
            if idx > 0:
                delay_ms = self.MIN_REQUEST_DELAY_MS + random.randint(0, 500)
                time.sleep(delay_ms / 1000)

            # Use first tab ID for the fetch (all tabs get the cached data)
            self._fetch_quote(tab_ids[0], symbol)

        # Schedule next poll
        self._schedule_next_poll()

    def _fetch_quote(self, tabId: str, symbol: str):
        """Fetch quote in background thread."""
        # Avoid duplicate fetches for same symbol
        with self._fetch_lock:
            if symbol in self._fetching:
                self.log.debug(f"Already fetching {symbol}, skipping")
                return
            self._fetching.add(symbol)

        # Capture values to avoid closure issues
        captured_tab_id = str(tabId)
        captured_symbol = str(symbol)

        thread = threading.Thread(
            target=self._fetch_in_thread,
            args=(captured_tab_id, captured_symbol),
            daemon=True
        )
        thread.start()

    def _fetch_in_thread(self, tabId: str, symbol: str):
        """Background thread to fetch quote from available sources."""
        quote: RealtimeQuote | None = None
        last_error: str = ""

        # Determine which sources to try
        sources_to_try = self._get_sources_for_symbol(symbol)

        for source in sources_to_try:
            try:
                self.log.debug(f"Trying {source.name} for {symbol}")
                quote = source.fetch_quote(symbol)

                # Remember which source worked (LRU update)
                if symbol in self._symbol_sources:
                    self._symbol_sources.move_to_end(symbol)
                self._symbol_sources[symbol] = source.name
                self.log.debug(f"Successfully fetched {symbol} from {source.name}")
                break

            except (ValueError, ConnectionError) as e:
                last_error = str(e)
                self.log.debug(f"{source.name} failed for {symbol}: {e}")
                continue
            except Exception as e:
                last_error = str(e)
                self.log.warning(f"{source.name} unexpected error for {symbol}: {e}")
                continue

        if quote:
            self._handle_success(tabId, symbol, quote)
        else:
            self._handle_error(tabId, symbol, last_error or "No data source available")

        # Remove from fetching set
        with self._fetch_lock:
            self._fetching.discard(symbol)

    def _get_sources_for_symbol(self, symbol: str) -> list[RealtimeDataSource]:
        """Get list of sources to try for a symbol, in priority order."""
        # If we know which source works, try it first
        preferred_source_name = self._symbol_sources.get(symbol)

        if preferred_source_name:
            # Reorder sources to put preferred first
            preferred = None
            others = []
            for source in self._sources:
                if source.name == preferred_source_name:
                    preferred = source
                else:
                    others.append(source)
            if preferred:
                return [preferred] + others

        # Otherwise, return sources that support this symbol
        return [s for s in self._sources if s.supports_symbol(symbol)]

    def _handle_success(self, tabId: str, symbol: str, quote: RealtimeQuote):
        """Handle successful quote fetch."""
        result = quote.to_dict()
        json_result = json.dumps(result)

        # Cache the data with LRU eviction
        # Move to end if exists (mark as recently used)
        if symbol in self._cached_data:
            self._cached_data.move_to_end(symbol)
        self._cached_data[symbol] = result

        # Evict oldest entries if cache exceeds limit
        while len(self._cached_data) > self.MAX_CACHE_SIZE:
            oldest_symbol = next(iter(self._cached_data))
            del self._cached_data[oldest_symbol]
            # Also clean up symbol_sources for evicted symbol
            self._symbol_sources.pop(oldest_symbol, None)

        # Success - reset error tracking
        self._consecutive_errors = 0
        self._current_backoff_ms = 0

        # Find ALL tabs that are polling this symbol and emit to each
        tabs_to_notify = [
            tid for tid, polling in self._polling_tabs.items()
            if polling and self._current_symbols.get(tid) == symbol
        ]

        # Emit success on main thread for ALL tabs with this symbol
        for tid in tabs_to_notify:
            QMetaObject.invokeMethod(
                self,
                "_emit_success",
                Qt.QueuedConnection,
                Q_ARG(str, tid),
                Q_ARG(str, json_result)
            )

        # Also emit price update for chart
        try:
            price = quote.price
            timestamp = int(datetime.now().timestamp())
            QMetaObject.invokeMethod(
                self,
                "_emit_price_update",
                Qt.QueuedConnection,
                Q_ARG(str, symbol),
                Q_ARG(float, price),
                Q_ARG(int, timestamp)
            )
        except Exception as e:
            self.log.debug(f"Could not emit price update: {e}")

    def _handle_error(self, tabId: str, symbol: str, error_msg: str):
        """Handle fetch error with backoff."""
        self.log.error(f"Realtime fetch error for {symbol}: {error_msg}")

        # Check for rate limiting
        if "429" in error_msg or "rate limit" in error_msg.lower():
            backoff_secs = random.randint(120, 300)
            self._rate_limited_until = time.time() + backoff_secs
            self._current_backoff_ms = backoff_secs * 1000
            self.log.warning(f"Rate limited! Backing off for {backoff_secs}s")
        elif "403" in error_msg or "denied" in error_msg.lower():
            backoff_secs = random.randint(300, 600)
            self._rate_limited_until = time.time() + backoff_secs
            self._current_backoff_ms = backoff_secs * 1000
            self.log.warning(f"Access denied! Backing off for {backoff_secs}s")
        else:
            self._apply_backoff()

        QMetaObject.invokeMethod(
            self,
            "_emit_error",
            Qt.QueuedConnection,
            Q_ARG(str, tabId),
            Q_ARG(str, error_msg)
        )

    def _apply_backoff(self):
        """Apply exponential backoff on error."""
        self._consecutive_errors += 1

        if self._consecutive_errors == 1:
            self._current_backoff_ms = self.BASE_POLL_INTERVAL_MS * 2
        else:
            self._current_backoff_ms = min(
                int(self._current_backoff_ms * self.BACKOFF_MULTIPLIER),
                self.MAX_BACKOFF_MS
            )

        self.log.warning(
            f"Backoff applied: {self._consecutive_errors} consecutive errors, "
            f"next interval: {self._current_backoff_ms}ms"
        )

    @Slot(str, str)
    def _emit_success(self, tabId: str, jsonData: str):
        """Main thread callback for success."""
        self.log.debug(f"Emitting realtime data for tab {tabId}")
        self.realtimeDataReady.emit(tabId, jsonData)

    @Slot(str, str)
    def _emit_error(self, tabId: str, error: str):
        """Main thread callback for error."""
        self.realtimeError.emit(tabId, error)

    @Slot(str, float, int)
    def _emit_price_update(self, symbol: str, price: float, timestamp: int):
        """Main thread callback for price update."""
        self.log.debug(f"Emitting price update: {symbol} = {price}")
        self.priceUpdate.emit(symbol, price, timestamp)

    @Slot()
    def clearCache(self):
        """Clear all cached data."""
        self._cached_data.clear()
        self._symbol_sources.clear()
        self.log.debug("Realtime cache cleared")

    @Slot(str, result=str)
    def getSourceForSymbol(self, symbol: str) -> str:
        """Get the name of the data source being used for a symbol."""
        return self._symbol_sources.get(symbol.upper().strip(), "")

    @Slot()
    def cleanup(self):
        """
        Clean up resources on application shutdown.
        Stops the timer and clears all state to prevent memory leaks.
        """
        self.log.info("RealtimeController cleanup started")

        # Stop the timer
        if self._timer:
            self._timer.stop()
            try:
                self._timer.timeout.disconnect()
            except (RuntimeError, TypeError):
                pass  # Signal might not be connected

        # Stop all polling
        self._polling_tabs.clear()

        # Clear caches
        self._cached_data.clear()
        self._symbol_sources.clear()
        self._current_symbols.clear()

        # Wait for any in-flight fetches to complete (with timeout)
        with self._fetch_lock:
            self._fetching.clear()

        self.log.info("RealtimeController cleanup completed")
