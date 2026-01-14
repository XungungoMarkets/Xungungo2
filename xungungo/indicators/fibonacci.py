from __future__ import annotations

from typing import Dict, Any, List
import numpy as np
import pandas as pd

from .base import IndicatorPlugin


def _safe_float_series(df: pd.DataFrame, col: str) -> np.ndarray:
    if col not in df.columns:
        return np.array([], dtype=float)
    return df[col].astype(float).to_numpy()


def _fib_levels(low: float, high: float, ratios: List[float]) -> Dict[float, float]:
    """
    Returns a dict mapping ratio -> price level, where:
      - ratio=0.0 => high
      - ratio=1.0 => low
    (classic retracement definition from high down to low)
    """
    span = high - low
    return {r: high - span * r for r in ratios}


def _fib_levels_up(low: float, high: float, ratios: List[float]) -> Dict[float, float]:
    """
    Returns a dict mapping ratio -> price level, where:
      - ratio=0.0 => low
      - ratio=1.0 => high
    (retracement definition from low up to high)
    """
    span = high - low
    return {r: low + span * r for r in ratios}


class FibonacciPlugin(IndicatorPlugin):
    id = "fibonacci"
    name = "Fibonacci"
    description = "Fibonacci retracement levels over a recent swing (lookback window)."

    def default_config(self) -> Dict[str, Any]:
        return {
            "mode": "auto",           # "auto" | "down" | "up"
            "lookback": 200,          # bars to consider to find swing high/low
            "high_col": "high",       # column used to find swing high
            "low_col": "low",         # column used to find swing low
            "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
            "extensions": [1.272, 1.618],  # optional; treated as >1 ratios beyond retracement
            "prefix": "fib",          # column prefix, e.g. fib_0_618
            "round": 6,               # decimals for column naming
        }

    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["auto", "down", "up"],
                    "title": "Mode",
                    "description": "auto: infer direction by which extreme happens last; down: high->low; up: low->high",
                },
                "lookback": {"type": "integer", "minimum": 5, "title": "Lookback"},
                "high_col": {"type": "string", "enum": ["high"], "title": "High column"},
                "low_col": {"type": "string", "enum": ["low"], "title": "Low column"},
                "ratios": {
                    "type": "array",
                    "items": {"type": "number"},
                    "title": "Retracement ratios",
                },
                "extensions": {
                    "type": "array",
                    "items": {"type": "number"},
                    "title": "Extensions (optional)",
                },
                "prefix": {"type": "string", "title": "Prefix"},
                "round": {"type": "integer", "minimum": 0, "maximum": 12, "title": "Rounding"},
            },
        }

    def presets(self) -> Dict[str, Dict[str, Any]]:
        """Predefined configurations for different Fibonacci setups."""
        return {
            "default": {
                "name": "Default Auto",
                "description": "Automatic direction detection, standard ratios",
                "config": {
                    "mode": "auto",
                    "lookback": 200,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
                    "extensions": [1.272, 1.618],
                    "prefix": "fib",
                    "round": 6,
                }
            },
            "retracement_only": {
                "name": "Retracement Only",
                "description": "Key retracement levels without extensions",
                "config": {
                    "mode": "auto",
                    "lookback": 200,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.236, 0.382, 0.5, 0.618, 0.786],
                    "extensions": [],
                    "prefix": "fib",
                    "round": 6,
                }
            },
            "short_term": {
                "name": "Short Term",
                "description": "Shorter lookback for day trading",
                "config": {
                    "mode": "auto",
                    "lookback": 50,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
                    "extensions": [1.272, 1.618],
                    "prefix": "fib",
                    "round": 6,
                }
            },
            "long_term": {
                "name": "Long Term",
                "description": "Extended lookback for swing trading",
                "config": {
                    "mode": "auto",
                    "lookback": 500,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
                    "extensions": [1.272, 1.618],
                    "prefix": "fib",
                    "round": 6,
                }
            },
            "extended": {
                "name": "Extended Targets",
                "description": "Include additional extension levels",
                "config": {
                    "mode": "auto",
                    "lookback": 200,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
                    "extensions": [1.272, 1.414, 1.618, 2.0, 2.618],
                    "prefix": "fib",
                    "round": 6,
                }
            }
        }

    def apply(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        high_col = str(config.get("high_col", "high"))
        low_col = str(config.get("low_col", "low"))
        if high_col not in df.columns or low_col not in df.columns:
            return df

        lookback = int(config.get("lookback", 200))
        lookback = max(5, min(lookback, len(df)))

        ratios = config.get("ratios", [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0])
        extensions = config.get("extensions", [1.272, 1.618])
        prefix = str(config.get("prefix", "fib"))
        rnd = int(config.get("round", 6))

        # sanitize ratios
        def _to_float_list(x) -> List[float]:
            if not isinstance(x, list):
                return []
            out = []
            for v in x:
                try:
                    out.append(float(v))
                except Exception:
                    pass
            return out

        ratios_f = _to_float_list(ratios)
        exts_f = [r for r in _to_float_list(extensions) if r > 1.0]

        # window extremes
        window = df.iloc[-lookback:].copy()
        highs = _safe_float_series(window, high_col)
        lows = _safe_float_series(window, low_col)
        if highs.size == 0 or lows.size == 0:
            return df

        hi_idx = int(np.nanargmax(highs))
        lo_idx = int(np.nanargmin(lows))
        swing_high = float(highs[hi_idx])
        swing_low = float(lows[lo_idx])

        # if degenerate, do nothing
        if not np.isfinite(swing_high) or not np.isfinite(swing_low) or swing_high == swing_low:
            return df

        mode = str(config.get("mode", "auto")).lower()

        # auto: pick direction by "which extreme occurs last" within lookback window
        # - if high occurs after low -> up swing (low->high)
        # - else -> down swing (high->low)
        if mode == "auto":
            direction = "up" if hi_idx > lo_idx else "down"
        elif mode in ("up", "down"):
            direction = mode
        else:
            direction = "down"

        # compute retracement levels + extensions
        # For "down": ratio 0 => high, 1 => low; extension >1 continues below low.
        # For "up":   ratio 0 => low, 1 => high; extension >1 continues above high.
        levels: Dict[str, float] = {}

        if direction == "down":
            base = _fib_levels(low=swing_low, high=swing_high, ratios=ratios_f)
            span = swing_high - swing_low
            for r, v in base.items():
                levels[str(r)] = float(v)
            for r in exts_f:
                # extension below low
                levels[str(r)] = float(swing_high - span * r)
        else:
            base = _fib_levels_up(low=swing_low, high=swing_high, ratios=ratios_f)
            span = swing_high - swing_low
            for r, v in base.items():
                levels[str(r)] = float(v)
            for r in exts_f:
                # extension above high
                levels[str(r)] = float(swing_low + span * r)

        # write to df (constant columns)
        out = df.copy()

        def _ratio_to_col(r_str: str) -> str:
            # stable column naming: fib_0_618 instead of fib_0.618
            try:
                r = round(float(r_str), rnd)
            except Exception:
                r = r_str
            s = str(r).replace(".", "_").replace("-", "m")
            return f"{prefix}_{s}"

        # store helpful metadata columns (also useful for debugging/backtesting)
        out[f"{prefix}_dir"] = direction
        out[f"{prefix}_swing_high"] = swing_high
        out[f"{prefix}_swing_low"] = swing_low
        out[f"{prefix}_lookback"] = lookback

        for r_str, price in levels.items():
            out[_ratio_to_col(r_str)] = float(price)

        return out

    def chart_series(self, config: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        Nota: LightweightCharts normalmente no es feliz con 8-12 líneas extra por defecto.
        Te dejo una selección típica; puedes ampliar según tu UI (selector de niveles).
        """
        cfg = config or self.default_config()
        prefix = cfg.get("prefix", "fib")
        return [
            {"id": f"{prefix}_0_382", "column": f"{prefix}_0_382", "type": "line", "pane": "main"},
            {"id": f"{prefix}_0_5",   "column": f"{prefix}_0_5",   "type": "line", "pane": "main"},
            {"id": f"{prefix}_0_618", "column": f"{prefix}_0_618", "type": "line", "pane": "main"},
        ]
