from __future__ import annotations
import json
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from typing import TYPE_CHECKING

from xungungo.core.logger import get_logger
if TYPE_CHECKING:
    from xungungo.data.yahoo_search import YahooSearchClient


class SearchController(QObject):
    """Controller for symbol search with autocomplete."""
    
    resultsChanged = Signal(str)  # Emits JSON array of results
    
    def __init__(self, search_client: YahooSearchClient, parent=None):
        super().__init__(parent)
        self.log = get_logger("xungungo.search")
        self.search_client = search_client
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)
        self._pending_query = ""
    
    @Slot(str)
    def search(self, query: str):
        """Debounced search - waits 300ms after last keystroke."""
        query = query.strip()
        self._pending_query = query
        
        if not query:
            self.resultsChanged.emit("[]")
            return
        
        # Restart timer on each keystroke
        self._search_timer.stop()
        self._search_timer.start(300)  # 300ms debounce
    
    def _perform_search(self):
        """Perform the actual search."""
        query = self._pending_query
        if not query:
            self.resultsChanged.emit("[]")
            return
        
        try:
            results = self.search_client.search(query, limit=10)
            
            # Convert to JSON
            results_json = [
                {
                    "symbol": r.symbol,
                    "longname": r.longname,
                    "exch": r.exch,
                    "typeDisp": r.type_disp,
                }
                for r in results
            ]
            
            self.resultsChanged.emit(json.dumps(results_json))
        except Exception as e:
            self.log.error("Search error: %s", e, exc_info=True)
            self.resultsChanged.emit("[]")
