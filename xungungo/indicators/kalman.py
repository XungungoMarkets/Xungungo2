from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from .base import IndicatorPlugin

def kalman_1d(z: np.ndarray, Q: float, R: float) -> np.ndarray:
    """
    1D Kalman filter implementation.
    
    Args:
        z: Observed values (measurements)
        Q: Process variance (how much the true value can change)
        R: Measurement variance (noise in observations)
    
    Returns:
        Filtered values
    """
    n = len(z)
    if n == 0:
        return np.array([])
    
    # Initialize
    x = z[0]  # Initial state estimate
    P = 1.0   # Initial estimation error covariance
    
    out = np.empty(n, dtype=float)
    out[0] = x
    
    for i in range(1, n):
        # Predict
        P = P + Q
        
        # Update
        K = P / (P + R)  # Kalman gain
        x = x + K * (z[i] - x)
        P = (1.0 - K) * P
        
        out[i] = x
    
    return out


class KalmanPlugin(IndicatorPlugin):
    """
    Kalman Filter Plugin
    
    Implements two 1D Kalman filters (fast and slow) over a price series.
    The fast filter responds quickly to price changes (higher Q).
    The slow filter is smoother and more stable (lower Q).
    
    Visualization:
    - Two lines (fast and slow)
    - Fill between them, colored by direction:
      * Green when fast > slow (bullish)
      * Red when fast < slow (bearish)
    """
    
    id = "kalman"
    name = "Kalman Filter"
    description = "Two 1D Kalman filters (fast/slow) with directional fill"

    def default_config(self) -> Dict[str, Any]:
        return {
            "source": "close",
            "fast": {
                "process_variance": 0.005012,  # Q: higher = more responsive
                "measurement_variance": 0.007079,  # R: higher = more smoothing
            },
            "slow": {
                "process_variance": 0.000029,  # Q: lower = more stable
                "measurement_variance": 0.001000,  # R
            },
            "show_cross_labels": True,  # Show markers by default
        }

    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["close", "open", "high", "low"],
                    "title": "Source",
                    "description": "Price series to filter"
                },
                "fast": {
                    "type": "object",
                    "title": "Fast Filter",
                    "properties": {
                        "process_variance": {
                            "type": "number",
                            "minimum": 0.0,
                            "title": "Q (Process Variance)",
                            "description": "Higher = more responsive to changes"
                        },
                        "measurement_variance": {
                            "type": "number",
                            "minimum": 0.0,
                            "title": "R (Measurement Variance)",
                            "description": "Higher = more smoothing"
                        },
                    }
                },
                "slow": {
                    "type": "object",
                    "title": "Slow Filter",
                    "properties": {
                        "process_variance": {
                            "type": "number",
                            "minimum": 0.0,
                            "title": "Q (Process Variance)",
                            "description": "Lower = more stable"
                        },
                        "measurement_variance": {
                            "type": "number",
                            "minimum": 0.0,
                            "title": "R (Measurement Variance)",
                            "description": "Higher = more smoothing"
                        },
                    }
                },
                "show_cross_labels": {
                    "type": "boolean",
                    "title": "Show Crossover Labels",
                    "description": "Add labels at each fast/slow crossover"
                },
            }
        }

    def presets(self) -> Dict[str, Dict[str, Any]]:
        """
        Predefined configurations for different trading styles.
        """
        return {
            "default": {
                "name": "Default",
                "description": "Balanced sensitivity for general trading",
                "config": {
                    "source": "close",
                    "fast": {
                        "process_variance": 0.005012,
                        "measurement_variance": 0.007079,
                    },
                    "slow": {
                        "process_variance": 0.000029,
                        "measurement_variance": 0.001000,
                    },
                    "show_cross_labels": True,
                }
            },
            "scalping": {
                "name": "Scalping",
                "description": "Ultra-responsive for short-term trades",
                "config": {
                    "source": "close",
                    "fast": {
                        "process_variance": 0.012000,
                        "measurement_variance": 0.003000,
                    },
                    "slow": {
                        "process_variance": 0.001500,
                        "measurement_variance": 0.000500,
                    },
                    "show_cross_labels": True,
                }
            },
            "swing_trading": {
                "name": "Swing Trading",
                "description": "Smooth filters for medium-term positions",
                "config": {
                    "source": "close",
                    "fast": {
                        "process_variance": 0.002000,
                        "measurement_variance": 0.015000,
                    },
                    "slow": {
                        "process_variance": 0.000010,
                        "measurement_variance": 0.003000,
                    },
                    "show_cross_labels": False,
                }
            },
            "trend_following": {
                "name": "Trend Following",
                "description": "Very smooth, minimal false signals",
                "config": {
                    "source": "close",
                    "fast": {
                        "process_variance": 0.000800,
                        "measurement_variance": 0.025000,
                    },
                    "slow": {
                        "process_variance": 0.000005,
                        "measurement_variance": 0.008000,
                    },
                    "show_cross_labels": False,
                }
            },
            "volatile_markets": {
                "name": "Volatile Markets",
                "description": "Aggressive filtering for high volatility",
                "config": {
                    "source": "close",
                    "fast": {
                        "process_variance": 0.015000,
                        "measurement_variance": 0.001000,
                    },
                    "slow": {
                        "process_variance": 0.003000,
                        "measurement_variance": 0.000200,
                    },
                    "show_cross_labels": True,
                }
            }
        }

    def apply(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Apply Kalman filters to the DataFrame."""
        if df is None or df.empty:
            return df
        
        source = config.get("source", "close")
        if source not in df.columns:
            return df
        
        # Get measurements
        z = df[source].astype(float).to_numpy()
        
        # Get parameters for fast filter
        fast_config = config.get("fast", {})
        fast_q = float(fast_config.get("process_variance", 1e-3))
        fast_r = float(fast_config.get("measurement_variance", 1e-2))
        
        # Get parameters for slow filter
        slow_config = config.get("slow", {})
        slow_q = float(slow_config.get("process_variance", 1e-4))
        slow_r = float(slow_config.get("measurement_variance", 1e-2))
        
        # Apply filters
        df = df.copy()
        df["kalman_fast"] = kalman_1d(z, Q=fast_q, R=fast_r)
        df["kalman_slow"] = kalman_1d(z, Q=slow_q, R=slow_r)

        # Compute crossovers
        diff = df["kalman_fast"].to_numpy() - df["kalman_slow"].to_numpy()
        cross = np.full(len(diff), np.nan, dtype=float)

        # Always compute crosses (visibility controlled by series definition)
        if len(diff) > 1:
            prev = diff[:-1]
            curr = diff[1:]
            cross_up = (prev <= 0) & (curr > 0)
            cross_down = (prev >= 0) & (curr < 0)
            cross[1:][cross_up] = 1.0
            cross[1:][cross_down] = -1.0

        df["kalman_cross"] = cross
        
        return df

    def chart_series(self, config: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        Define visualization: two lines + fill between them.

        No JavaScript custom needed! The advanced_renderer.js handles
        the fill_between type automatically.
        """
        series = [
            # Fast line (responsive)
            {
                "id": "kalman_fast",
                "column": "kalman_fast",
                "type": "line",
                "pane": "main",
            },
            # Slow line (stable)
            {
                "id": "kalman_slow",
                "column": "kalman_slow",
                "type": "line",
                "pane": "main",
            },
            # Fill between fast and slow
            {
                "id": "kalman_fill",
                "type": "fill_between",
                "series1": "kalman_fast",
                "series2": "kalman_slow",
                "upColor": "rgba(38,166,154,0.18)",    # Green when fast > slow
                "downColor": "rgba(239,83,80,0.18)",   # Red when fast < slow
                "pane": "main",
            },
        ]

        # Add markers series only if enabled in config
        cfg = config or self.default_config()
        if cfg.get("show_cross_labels", False):
            series.append({
                "id": "kalman_cross_markers",
                "type": "markers",
                "series": "candles",
                "column": "kalman_cross",
                "upColor": "#26a69a",
                "downColor": "#ef5350",
                "shapeUp": "arrowUp",
                "shapeDown": "arrowDown",
                "textUp": "▲",
                "textDown": "▼",
                "pane": "main",
            })

        return series
