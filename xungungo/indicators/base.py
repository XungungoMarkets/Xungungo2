from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any, List, Literal

# Tipos de renderizado especiales disponibles
RenderType = Literal["line", "histogram", "area", "baseline", "fill_between", "band", "candlestick", "markers"]

class IndicatorPlugin(ABC):
    id: str
    name: str
    description: str

    @abstractmethod
    def default_config(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def config_schema(self) -> Dict[str, Any]:
        ...

    def presets(self) -> Dict[str, Dict[str, Any]]:
        """
        Return predefined presets for this plugin.

        Returns a dictionary where:
        - Keys are preset IDs (e.g., "conservative", "aggressive")
        - Values are dictionaries with:
          - "name": Display name for the preset
          - "description": Brief description of what this preset does
          - "config": The configuration values for this preset

        Example:
        {
            "conservative": {
                "name": "Conservative",
                "description": "Slow response, minimal noise",
                "config": {"fast": {...}, "slow": {...}}
            }
        }
        """
        return {}

    @abstractmethod
    def apply(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        ...

    @abstractmethod
    def chart_series(self, config: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        Describe series to render with advanced options.
        
        Basic line example:
        [{
            "id": "ma_20",
            "column": "ma_20",
            "type": "line",
            "pane": "main"
        }]
        
        Fill between two lines example:
        [{
            "id": "kalman_fast",
            "column": "kalman_fast",
            "type": "line",
            "pane": "main"
        }, {
            "id": "kalman_slow",
            "column": "kalman_slow",
            "type": "line",
            "pane": "main"
        }, {
            "id": "kalman_fill",
            "type": "fill_between",
            "series1": "kalman_fast",
            "series2": "kalman_slow",
            "upColor": "rgba(38,166,154,0.2)",
            "downColor": "rgba(239,83,80,0.2)",
            "pane": "main"
        }]
        
        Band (single series with upper/lower bounds) example:
        [{
            "id": "bb_middle",
            "column": "bb_middle",
            "type": "line",
            "pane": "main"
        }, {
            "id": "bb_band",
            "type": "band",
            "upperColumn": "bb_upper",
            "lowerColumn": "bb_lower",
            "fillColor": "rgba(33,150,243,0.1)",
            "pane": "main"
        }]
        
        Markers (labels on a target series) example:
        [{
            "id": "cross_markers",
            "type": "markers",
            "series": "ma_20",
            "column": "ma_cross",
            "textUp": "UP",
            "textDown": "DOWN"
        }]
        """
        ...

    def javascript_code(self) -> str | None:
        """
        Optional: Return custom JavaScript code for advanced rendering.
        This code will be injected into the page.
        
        Return None for standard rendering (most plugins).
        Return JS code string for custom renderers.
        """
        return None
