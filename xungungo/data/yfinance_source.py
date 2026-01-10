from __future__ import annotations
import pandas as pd
import yfinance as yf

from .datasource_base import DataSource
from .normalize import normalize_yfinance

class YFinanceDataSource(DataSource):
    def fetch_ohlcv(self, symbol: str, interval: str = "1d", period: str = "1y") -> pd.DataFrame:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
        if df is None or df.empty:
            raise ValueError(f"No data for symbol: {symbol}")
        return normalize_yfinance(df)
