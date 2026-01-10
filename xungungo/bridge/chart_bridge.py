from __future__ import annotations
import json
from PySide6.QtCore import QObject, Signal, Slot, Property
from PySide6.QtQml import QQmlEngine

class ChartBridge(QObject):
    """Bridge between Python and JavaScript chart code via WebChannel."""
    
    push = Signal(str)  # Emits JSON string to JavaScript
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_ready = False
        self.setObjectName("chartBridge")
        
        # CRITICAL: Set QML ownership to prevent garbage collection
        if parent and isinstance(parent, QObject):
            QQmlEngine.setObjectOwnership(self, QQmlEngine.ObjectOwnership.CppOwnership)
        
        print(f"ChartBridge created, parent: {parent}")
    
    @Slot()
    def ready(self):
        """Called by JavaScript when WebChannel is initialized."""
        self._is_ready = True
        print("ChartBridge: JavaScript side is ready")
    
    @Property(bool)
    def isReady(self):
        """Property version of is_ready for QML."""
        return self._is_ready
    
    def is_ready(self) -> bool:
        """Check if JavaScript side has signaled ready."""
        return self._is_ready
    
    def send_all(self, candles: list, indicators: dict | None = None):
        """Send complete chart data (candles + indicators)."""
        if not self._is_ready:
            print("ChartBridge: Not ready yet, sending anyway...")
        
        payload = {
            "type": "all",
            "candles": candles,
            "indicators": indicators or {}
        }
        
        json_str = json.dumps(payload, separators=(',', ':'))
        print(f"ChartBridge: Sending 'all' with {len(candles)} candles, {len(indicators or {})} indicators")
        self.push.emit(json_str)
    
    def send_indicators(self, indicators: dict):
        """Send only indicator data (updates without resetting candles)."""
        if not self._is_ready:
            print("ChartBridge: Not ready yet, sending indicators anyway...")
        
        payload = {
            "type": "indicators",
            "indicators": indicators
        }
        
        json_str = json.dumps(payload, separators=(',', ':'))
        print(f"ChartBridge: Sending 'indicators' with {len(indicators)} series")
        self.push.emit(json_str)