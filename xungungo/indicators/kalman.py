from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from .base import IndicatorPlugin

def kalman_1d(z: np.ndarray, Q: float, R: float) -> np.ndarray:
    n = len(z)
    if n == 0:
        return np.array([])
    x = z[0]
    P = 1.0
    out = np.empty(n, dtype=float)
    out[0] = x
    for i in range(1, n):
        # predict
        P = P + Q
        # update
        K = P / (P + R)
        x = x + K * (z[i] - x)
        P = (1.0 - K) * P
        out[i] = x
    return out

class KalmanPlugin(IndicatorPlugin):
    id = "kalman"
    name = "Kalman"
    description = "Two 1D Kalman filters (fast/slow) over a source series."

    def default_config(self) -> Dict[str, Any]:
        return {
            "source": "close",
            "fast": {"process_variance": 1e-3, "measurement_variance": 1e-2},
            "slow": {"process_variance": 1e-4, "measurement_variance": 1e-2},
        }

    def config_schema(self) -> Dict[str, Any]:
        # JSON-schema-like minimal
        return {
            "type": "object",
            "properties": {
                "source": {"type": "string", "enum": ["close"], "title": "Source"},
                "fast": {
                    "type": "object",
                    "title": "Fast",
                    "properties": {
                        "process_variance": {"type": "number", "title": "Q"},
                        "measurement_variance": {"type": "number", "title": "R"},
                    }
                },
                "slow": {
                    "type": "object",
                    "title": "Slow",
                    "properties": {
                        "process_variance": {"type": "number", "title": "Q"},
                        "measurement_variance": {"type": "number", "title": "R"},
                    }
                },
            }
        }

    def apply(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        src = config.get("source", "close")
        if src not in df.columns:
            return df
        z = df[src].astype(float).to_numpy()

        fq = float(config.get("fast", {}).get("process_variance", 1e-3))
        fr = float(config.get("fast", {}).get("measurement_variance", 1e-2))
        sq = float(config.get("slow", {}).get("process_variance", 1e-4))
        sr = float(config.get("slow", {}).get("measurement_variance", 1e-2))

        df = df.copy()
        df["kalman_fast"] = kalman_1d(z, Q=fq, R=fr)
        df["kalman_slow"] = kalman_1d(z, Q=sq, R=sr)
        return df

    def chart_series(self) -> List[Dict[str, Any]]:
        return [
            {"id": "kalman_fast", "column": "kalman_fast", "type": "line", "pane": "main"},
            {"id": "kalman_slow", "column": "kalman_slow", "type": "line", "pane": "main"},
        ]
