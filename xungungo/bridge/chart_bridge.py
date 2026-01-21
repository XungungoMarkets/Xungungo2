from __future__ import annotations
import json
from PySide6.QtCore import QObject, Signal, Slot, Property
from PySide6.QtQml import QQmlEngine

from xungungo.core.logger import get_logger

class ChartBridge(QObject):
    """Bridge between Python and JavaScript chart code via WebChannel."""
    
    push = Signal(str)  # Emits JSON string to JavaScript
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log = get_logger("xungungo.bridge")
        self._is_ready = False
        self.setObjectName("chartBridge")
        
        # CRITICAL: Set QML ownership to prevent garbage collection
        if parent and isinstance(parent, QObject):
            QQmlEngine.setObjectOwnership(self, QQmlEngine.ObjectOwnership.CppOwnership)
        
        self.log.debug("ChartBridge created, parent: %s", parent)
    
    @Slot()
    def ready(self):
        """Called by JavaScript when WebChannel is initialized."""
        self._is_ready = True
        self.log.debug("ChartBridge: JavaScript side is ready")
    
    @Property(bool)
    def isReady(self):
        """Property version of is_ready for QML."""
        return self._is_ready
    
    def is_ready(self) -> bool:
        """Check if JavaScript side has signaled ready."""
        return self._is_ready
    
    def send_all(self, candles: list, indicators: dict | None = None, series_defs: list | None = None):
        """Send complete chart data (candles + indicators + series defs)."""
        if not self._is_ready:
            self.log.debug("ChartBridge: Not ready yet, sending anyway...")
        
        payload = {
            "type": "all",
            "candles": candles,
            "indicators": indicators or {},
            "seriesDefs": series_defs or []
        }
        
        json_str = json.dumps(payload, separators=(',', ':'))
        self.log.debug(
            "ChartBridge: Sending 'all' with %d candles, %d indicators",
            len(candles),
            len(indicators or {})
        )
        self.push.emit(json_str)
    
    def send_indicators(self, indicators: dict, series_defs: list | None = None):
        """Send only indicator data (updates without resetting candles)."""
        if not self._is_ready:
            self.log.debug("ChartBridge: Not ready yet, sending indicators anyway...")
        
        payload = {
            "type": "indicators",
            "indicators": indicators,
            "seriesDefs": series_defs or []
        }
        
        json_str = json.dumps(payload, separators=(',', ':'))
        self.log.debug("ChartBridge: Sending 'indicators' with %d series", len(indicators))
        self.push.emit(json_str)
