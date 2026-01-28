from __future__ import annotations
import json
import threading
from PySide6.QtCore import QObject, Signal, Slot, QMetaObject, Qt, Q_ARG
import yfinance as yf

from xungungo.core.logger import get_logger

# Use a separate lock for analysis to avoid conflicts with ticker controller
_analysis_lock = threading.Lock()


def _get_info(ticker, log) -> dict:
    """Extract relevant info fields."""
    try:
        log.debug("Fetching ticker.info")
        info = ticker.info
        if not info:
            return {}

        # Select relevant fields for analysis
        relevant_fields = [
            # Basic info
            "shortName", "longName", "symbol", "currency", "exchange",
            "quoteType", "sector", "industry", "country", "city",
            "website", "longBusinessSummary",
            # Valuation
            "marketCap", "enterpriseValue", "trailingPE", "forwardPE",
            "pegRatio", "priceToBook", "priceToSalesTrailing12Months",
            # Price info
            "currentPrice", "targetHighPrice", "targetLowPrice",
            "targetMeanPrice", "targetMedianPrice",
            "previousClose", "open", "dayLow", "dayHigh",
            "fiftyTwoWeekLow", "fiftyTwoWeekHigh",
            "fiftyDayAverage", "twoHundredDayAverage",
            # Dividends
            "dividendRate", "dividendYield", "payoutRatio",
            "exDividendDate", "lastDividendValue", "lastDividendDate",
            # Financial metrics
            "totalRevenue", "revenuePerShare", "revenueGrowth",
            "grossMargins", "ebitdaMargins", "operatingMargins", "profitMargins",
            "grossProfits", "ebitda", "operatingCashflow", "freeCashflow",
            "totalCash", "totalDebt", "debtToEquity",
            "returnOnAssets", "returnOnEquity",
            "earningsGrowth", "earningsQuarterlyGrowth",
            # Shares
            "sharesOutstanding", "floatShares", "sharesShort",
            "shortRatio", "shortPercentOfFloat",
            "heldPercentInsiders", "heldPercentInstitutions",
            # Other
            "beta", "trailingEps", "forwardEps",
            "bookValue", "enterpriseToRevenue", "enterpriseToEbitda",
            "fullTimeEmployees",
            "recommendationKey", "recommendationMean", "numberOfAnalystOpinions",
        ]

        result = {}
        for field in relevant_fields:
            if field in info and info[field] is not None:
                value = info[field]
                # Handle special types
                if hasattr(value, 'timestamp'):  # datetime
                    value = int(value.timestamp())
                result[field] = value

        return result
    except Exception as e:
        log.error(f"Error getting info: {e}")
        return {"error": str(e)}


def _get_major_holders(ticker, log) -> list:
    """Get major holders data."""
    # Friendly names for technical field names
    FRIENDLY_NAMES = {
        "insidersPercentHeld": "Held by Insiders",
        "institutionsPercentHeld": "Held by Institutions",
        "institutionsFloatPercentHeld": "Institutions (Float)",
        "institutionsCount": "Number of Institutions",
    }

    try:
        log.debug("Fetching major_holders")
        holders = ticker.major_holders
        if holders is None or holders.empty:
            return []

        # Convert to list of dicts
        # DataFrame structure: index contains description, column 0 contains value
        result = []
        for idx, row in holders.iterrows():
            value = row.iloc[0] if len(row) > 0 else ""
            key = str(idx)

            # Format percentage values
            if isinstance(value, float) and value < 1:
                value = f"{value * 100:.2f}%"
            elif isinstance(value, (int, float)):
                value = f"{int(value):,}"
            else:
                value = str(value)

            # Use friendly name if available
            description = FRIENDLY_NAMES.get(key, key)

            result.append({
                "value": value,
                "description": description,
            })
        return result
    except Exception as e:
        log.debug(f"No major holders: {e}")
        return []


def _get_institutional_holders(ticker, log) -> list:
    """Get institutional holders data."""
    try:
        log.debug("Fetching institutional_holders")
        holders = ticker.institutional_holders
        if holders is None or holders.empty:
            return []

        # Log actual column names for debugging
        log.debug(f"Institutional holders columns: {list(holders.columns)}")

        # Column name mapping - yfinance column names may vary
        PCT_OUT = "% Out"
        COLUMN_MAPPING = {
            "pctHeld": PCT_OUT,
            "pctheld": PCT_OUT,
            "% Held": PCT_OUT,
            "pctOut": PCT_OUT,
        }

        # Convert to list of dicts (top 10)
        result = []
        for idx, row in holders.head(10).iterrows():
            holder_data = {}
            for col in holders.columns:
                value = row[col]
                if hasattr(value, 'timestamp'):  # datetime
                    value = int(value.timestamp())
                elif hasattr(value, 'item'):  # numpy types
                    value = value.item()
                # Normalize column name
                normalized_col = COLUMN_MAPPING.get(col, col)
                holder_data[normalized_col] = value
            result.append(holder_data)
        return result
    except Exception as e:
        log.debug(f"No institutional holders: {e}")
        return []


def _get_recommendations(ticker, log) -> list:
    """Get analyst recommendations."""
    try:
        log.debug("Fetching recommendations")
        recs = ticker.recommendations
        if recs is None or recs.empty:
            return []

        # Get last 10 recommendations
        result = []
        for idx, row in recs.tail(10).iterrows():
            rec_data = {"date": str(idx)}
            for col in recs.columns:
                value = row[col]
                if hasattr(value, 'item'):  # numpy types
                    value = value.item()
                rec_data[col] = value
            result.append(rec_data)
        return result
    except Exception as e:
        log.debug(f"No recommendations: {e}")
        return []


def _fetch_analysis_data(symbol: str, log) -> dict:
    """Fetch all analysis data for a symbol. Runs in background thread."""
    log.debug(f"Creating yfinance Ticker for {symbol}")
    ticker = yf.Ticker(symbol)

    data = {
        "symbol": symbol,
        "info": _get_info(ticker, log),
        "majorHolders": _get_major_holders(ticker, log),
        "institutionalHolders": _get_institutional_holders(ticker, log),
        "recommendations": _get_recommendations(ticker, log),
    }

    return data


class AnalysisController(QObject):
    """Controller for fetching and managing stock analysis data."""

    # Signal emitted when analysis data is ready: (symbol, json_data)
    analysisReady = Signal(str, str)
    # Signal emitted on error: (symbol, error_message)
    analysisError = Signal(str, str)
    # Signal for loading state: (symbol, is_loading)
    loadingChanged = Signal(str, bool)

    def __init__(self):
        super().__init__()
        self.log = get_logger("xungungo.analysis")

        # Cache for loaded analysis data
        self._cache: dict[str, str] = {}
        # Track loading state per symbol
        self._loading: set[str] = set()
        # Keep reference to running threads
        self._running_threads: dict[str, threading.Thread] = {}

    @Slot(str)
    def loadAnalysis(self, symbol: str):
        """Load analysis data for a symbol. Called from QML."""
        if not symbol:
            return

        symbol = symbol.upper().strip()

        # Check cache first
        if symbol in self._cache:
            self.log.debug(f"Analysis cache hit for {symbol}")
            self.analysisReady.emit(symbol, self._cache[symbol])
            return

        # Check if already loading
        if symbol in self._loading:
            self.log.debug(f"Analysis already loading for {symbol}")
            return

        self.log.info(f"Loading analysis for {symbol}")
        self._loading.add(symbol)
        self.loadingChanged.emit(symbol, True)

        # Create and start background thread
        thread = threading.Thread(
            target=self._fetch_in_thread,
            args=(symbol,),
            daemon=True
        )
        self._running_threads[symbol] = thread
        thread.start()

    def _fetch_in_thread(self, symbol: str):
        """Background thread function to fetch analysis data."""
        try:
            self.log.debug(f"Analysis thread started for {symbol}")

            # Acquire lock and fetch data
            with _analysis_lock:
                self.log.debug(f"Analysis lock acquired for {symbol}")
                data = _fetch_analysis_data(symbol, self.log)
                self.log.debug(f"Analysis data fetched for {symbol}")

            json_data = json.dumps(data)
            self.log.debug(f"Analysis JSON created for {symbol}, length={len(json_data)}")

            # Emit success signal on main thread
            QMetaObject.invokeMethod(
                self,
                "_emit_success",
                Qt.QueuedConnection,
                Q_ARG(str, symbol),
                Q_ARG(str, json_data)
            )

        except Exception as e:
            error_msg = str(e)
            self.log.error(f"Analysis fetch error for {symbol}: {error_msg}")

            # Emit error signal on main thread
            QMetaObject.invokeMethod(
                self,
                "_emit_error",
                Qt.QueuedConnection,
                Q_ARG(str, symbol),
                Q_ARG(str, error_msg)
            )

    @Slot(str, str)
    def _emit_success(self, symbol: str, json_data: str):
        """Called on main thread to emit success signals."""
        self.log.debug(f"Analysis success callback for {symbol}")
        self._loading.discard(symbol)
        self._running_threads.pop(symbol, None)
        self._cache[symbol] = json_data
        self.loadingChanged.emit(symbol, False)
        self.analysisReady.emit(symbol, json_data)
        self.log.info(f"Analysis loaded for {symbol}")

    @Slot(str, str)
    def _emit_error(self, symbol: str, error: str):
        """Called on main thread to emit error signals."""
        self._loading.discard(symbol)
        self._running_threads.pop(symbol, None)
        self.loadingChanged.emit(symbol, False)
        self.analysisError.emit(symbol, error)
        self.log.error(f"Analysis error for {symbol}: {error}")

    @Slot(str, result=bool)
    def isLoading(self, symbol: str) -> bool:
        """Check if analysis is currently loading for a symbol."""
        return symbol.upper().strip() in self._loading

    @Slot(str, result=str)
    def getCachedAnalysis(self, symbol: str) -> str:
        """Get cached analysis data if available."""
        symbol = symbol.upper().strip()
        return self._cache.get(symbol, "")

    @Slot()
    def clearCache(self):
        """Clear the analysis cache."""
        self._cache.clear()
        self.log.debug("Analysis cache cleared")
