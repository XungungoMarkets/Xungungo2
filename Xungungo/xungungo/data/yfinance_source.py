from datetime import datetime
from typing import Optional

import pandas as pd
import yfinance as yf

from .datasource_base import DataSource
from .normalize import normalize_ohlcv


class YFinanceDataSource(DataSource):
    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        data = yf.download(
            symbol,
            interval=interval,
            start=start,
            end=end,
            progress=False,
            auto_adjust=False,
        )
        return normalize_ohlcv(data)
