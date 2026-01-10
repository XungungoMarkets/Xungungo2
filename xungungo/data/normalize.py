from __future__ import annotations
import pandas as pd

STD_COLS = ["timestamp", "open", "high", "low", "close", "volume"]

def _flatten_col(c):
    # yfinance can return MultiIndex columns or tuple-like entries
    if isinstance(c, tuple) and len(c) > 0:
        return str(c[0])
    return str(c)

def normalize_yfinance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize yfinance OHLCV into a standard DataFrame:
      timestamp (UTC tz-aware)
      open, high, low, close, volume

    Handles MultiIndex/tuple columns (e.g. ('Open','AAPL')).
    """
    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns.to_list()]
    else:
        df.columns = [_flatten_col(c) for c in df.columns]

    cols_map = {str(c).lower(): str(c) for c in df.columns}

    def pick(name: str) -> str:
        return cols_map.get(name.lower(), name.capitalize())

    out = pd.DataFrame(index=df.index.copy())
    out["open"] = pd.to_numeric(df[pick("open")], errors="coerce")
    out["high"] = pd.to_numeric(df[pick("high")], errors="coerce")
    out["low"]  = pd.to_numeric(df[pick("low")], errors="coerce")
    out["close"]= pd.to_numeric(df[pick("close")], errors="coerce")
    out["volume"]= pd.to_numeric(df[pick("volume")], errors="coerce").fillna(0)

    idx = out.index
    if getattr(idx, "tz", None) is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    out["timestamp"] = idx

    out = out.reset_index(drop=True)
    out = out.dropna(subset=["open", "high", "low", "close"])
    out = out.sort_values("timestamp").reset_index(drop=True)

    out["open"] = out["open"].astype(float)
    out["high"] = out["high"].astype(float)
    out["low"] = out["low"].astype(float)
    out["close"] = out["close"].astype(float)
    out["volume"] = out["volume"].astype(float)

    return out[STD_COLS]
