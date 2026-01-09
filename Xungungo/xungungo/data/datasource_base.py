from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import pandas as pd


class DataSource(ABC):
    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError
