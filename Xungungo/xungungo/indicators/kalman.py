from typing import Dict, List

import numpy as np
import pandas as pd

from xungungo.core.models import ChartSeries

from .base import IndicatorBase


class KalmanIndicator(IndicatorBase):
    id = "kalman"
    name = "Kalman"
    description = "Filtro Kalman 1D (fast/slow) aplicado al precio de cierre."

    def default_config(self) -> Dict:
        return {
            "source": "close",
            "fast.process_variance": 1e-5,
            "fast.measurement_variance": 1e-2,
            "slow.process_variance": 1e-6,
            "slow.measurement_variance": 1e-1,
        }

    def config_schema(self) -> Dict:
        return {
            "fields": [
                {
                    "key": "source",
                    "label": "Source",
                    "type": "select",
                    "options": ["close", "open", "high", "low"],
                },
                {
                    "key": "fast.process_variance",
                    "label": "Fast Q",
                    "type": "number",
                    "min": 1e-8,
                    "step": 1e-6,
                },
                {
                    "key": "fast.measurement_variance",
                    "label": "Fast R",
                    "type": "number",
                    "min": 1e-8,
                    "step": 1e-4,
                },
                {
                    "key": "slow.process_variance",
                    "label": "Slow Q",
                    "type": "number",
                    "min": 1e-8,
                    "step": 1e-7,
                },
                {
                    "key": "slow.measurement_variance",
                    "label": "Slow R",
                    "type": "number",
                    "min": 1e-8,
                    "step": 1e-3,
                },
            ]
        }

    def apply(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        source = config.get("source", "close")
        series = df[source].to_numpy(dtype=float)
        fast = self._kalman(series, config["fast.process_variance"], config["fast.measurement_variance"])
        slow = self._kalman(series, config["slow.process_variance"], config["slow.measurement_variance"])
        df["kalman_fast"] = fast
        df["kalman_slow"] = slow
        return df

    def chart_series(self) -> List[ChartSeries]:
        return [
            ChartSeries(series_id="kalman_fast", name="Kalman Fast", column="kalman_fast", color="#33C3F0"),
            ChartSeries(series_id="kalman_slow", name="Kalman Slow", column="kalman_slow", color="#FF7A59"),
        ]

    def _kalman(self, data: np.ndarray, q: float, r: float) -> np.ndarray:
        x = data[0]
        p = 1.0
        out = []
        for measurement in data:
            p = p + q
            k = p / (p + r)
            x = x + k * (measurement - x)
            p = (1 - k) * p
            out.append(x)
        return np.array(out)
