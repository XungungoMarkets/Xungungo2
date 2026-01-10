from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd

class DataSource(ABC):
    @abstractmethod
    def fetch_ohlcv(self, symbol: str, interval: str = "1d", period: str = "1y") -> pd.DataFrame:
        raise NotImplementedError
