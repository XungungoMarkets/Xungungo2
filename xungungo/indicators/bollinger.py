from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from .base import IndicatorPlugin


def calculate_bollinger_bands(prices: np.ndarray, period: int = 20, std_dev: float = 2.0):
    """Calculate Bollinger Bands."""
    if len(prices) < period:
        return np.full(len(prices), np.nan), np.full(len(prices), np.nan), np.full(len(prices), np.nan)
    
    # Calculate SMA
    sma = np.convolve(prices, np.ones(period)/period, mode='same')
    
    # Fix edges
    for i in range(period-1):
        sma[i] = np.mean(prices[:i+1])
    
    # Calculate standard deviation
    std = np.zeros(len(prices))
    for i in range(period-1, len(prices)):
        std[i] = np.std(prices[i-period+1:i+1])
    
    # Calculate bands
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    
    # Set initial values to NaN
    sma[:period-1] = np.nan
    upper[:period-1] = np.nan
    lower[:period-1] = np.nan
    
    return sma, upper, lower


class BollingerBandsPlugin(IndicatorPlugin):
    """
    Bollinger Bands Plugin
    
    Ejemplo de plugin que usa el sistema de 'band' rendering.
    El fill entre las bandas superior e inferior se hace automáticamente
    sin necesidad de JavaScript custom.
    """
    
    id = "bollinger"
    name = "Bollinger Bands"
    description = "Volatility bands around a moving average"

    def default_config(self) -> Dict[str, Any]:
        return {
            "source": "close",
            "period": 20,
            "std_dev": 2.0,
            "show_middle": True,
        }

    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["close", "open", "high", "low"],
                    "title": "Source",
                    "description": "Price series to calculate bands from"
                },
                "period": {
                    "type": "integer",
                    "minimum": 2,
                    "maximum": 200,
                    "title": "Period",
                    "description": "Number of periods for SMA calculation"
                },
                "std_dev": {
                    "type": "number",
                    "minimum": 0.5,
                    "maximum": 5.0,
                    "title": "Standard Deviation",
                    "description": "Number of standard deviations for bands"
                },
                "show_middle": {
                    "type": "boolean",
                    "title": "Show Middle Line",
                    "description": "Show the middle SMA line"
                },
            }
        }

    def presets(self) -> Dict[str, Dict[str, Any]]:
        """Predefined configurations for different trading styles."""
        return {
            "default": {
                "name": "Default (20, 2)",
                "description": "Standard Bollinger Bands settings",
                "config": {
                    "source": "close",
                    "period": 20,
                    "std_dev": 2.0,
                    "show_middle": True,
                }
            },
            "tight": {
                "name": "Tight Bands (20, 1.5)",
                "description": "Narrower bands for ranging markets",
                "config": {
                    "source": "close",
                    "period": 20,
                    "std_dev": 1.5,
                    "show_middle": True,
                }
            },
            "wide": {
                "name": "Wide Bands (20, 3)",
                "description": "Wider bands for volatile markets",
                "config": {
                    "source": "close",
                    "period": 20,
                    "std_dev": 3.0,
                    "show_middle": True,
                }
            },
            "fast": {
                "name": "Fast (10, 2)",
                "description": "Short period for quick reversals",
                "config": {
                    "source": "close",
                    "period": 10,
                    "std_dev": 2.0,
                    "show_middle": True,
                }
            },
            "slow": {
                "name": "Slow (50, 2)",
                "description": "Long period for trend following",
                "config": {
                    "source": "close",
                    "period": 50,
                    "std_dev": 2.0,
                    "show_middle": True,
                }
            }
        }

    def apply(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        
        source = config.get("source", "close")
        if source not in df.columns:
            return df
        
        period = int(config.get("period", 20))
        std_dev = float(config.get("std_dev", 2.0))
        
        prices = df[source].astype(float).to_numpy()
        
        sma, upper, lower = calculate_bollinger_bands(prices, period, std_dev)
        
        df = df.copy()
        df["bb_middle"] = sma
        df["bb_upper"] = upper
        df["bb_lower"] = lower
        
        return df

    def chart_series(self, config: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        Usa el sistema 'band' para renderizar el fill automáticamente.
        No necesita JavaScript custom!
        """
        cfg = config or self.default_config()
        series = []

        # Línea del medio (opcional, basado en configuración)
        if cfg.get("show_middle", True):
            series.append({
                "id": "bb_middle",
                "column": "bb_middle",
                "type": "line",
                "pane": "main",
            })

        # Band fill entre upper y lower
        series.append({
            "id": "bb_band",
            "type": "band",
            "upperColumn": "bb_upper",
            "lowerColumn": "bb_lower",
            "fillColor": "rgba(33,150,243,0.15)",
            "pane": "main",
        })

        return series