from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any, List

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

    @abstractmethod
    def apply(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        ...

    @abstractmethod
    def chart_series(self) -> List[Dict[str, Any]]:
        """Describe series to render: e.g. [{id:'kalman_fast', column:'kalman_fast', type:'line', pane:'main'}]"""
        ...
