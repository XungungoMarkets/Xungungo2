from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd

class DataSource(ABC):
    @abstractmethod
    def fetch_ohlcv(self, symbol: str, interval: str = "1d", period: str = "1y") -> pd.DataFrame:
        raise NotImplementedError

    def normalize_interval_period(self, interval: str, period: str) -> tuple[str, str]:
        """Normalize interval/period by clamping period DOWN if needed."""
        return interval, period

    def normalize_period_adjusting_interval(self, interval: str, period: str) -> tuple[str, str]:
        """Normalize by adjusting interval UP if period requires it."""
        return interval, period

    def get_min_interval_for_period(self, period: str) -> str:
        """Get minimum interval that supports the given period."""
        return "1d"
