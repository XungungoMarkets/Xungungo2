from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd

class DataSource(ABC):
    @abstractmethod
    def fetch_ohlcv(self, symbol: str, interval: str = "1d", period: str = "1y") -> pd.DataFrame:
        raise NotImplementedError

    def normalize_interval_period(self, interval: str, period: str) -> tuple[str, str]:
        """Normalize interval/period to what the datasource supports."""
        return interval, period
