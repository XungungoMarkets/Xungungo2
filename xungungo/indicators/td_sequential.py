from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from .base import IndicatorPlugin

# Import from external tdsequential library
# Install with: pip install git+https://github.com/Fiambre/TDSequential.git
# Import from core directly to avoid pulling in the optional matplotlib plot module
from tdsequential.core import calculate_td_sequential


def calculate_tdst_levels(
    df: pd.DataFrame,
    high_col: str = "High",
    low_col: str = "Low",
) -> pd.DataFrame:
    """
    Calculate TDST (TD Setup Trend) support and resistance levels.

    TDST Buy: Lowest low of bars 1-9 during Buy Setup (support)
    TDST Sell: Highest high of bars 1-9 during Sell Setup (resistance)

    Levels persist until price breaks through them.

    Args:
        df: DataFrame with TD Sequential columns calculated (must have numeric index)
        high_col: Name of high column
        low_col: Name of low column

    Returns:
        DataFrame with additional columns:
        - tdst_buy: Support level (lowest low of Buy Setup bars 1-9)
        - tdst_sell: Resistance level (highest high of Sell Setup bars 1-9)
    """
    df = df.copy()
    n = len(df)

    high = df[high_col].astype(float).values
    low = df[low_col].astype(float).values
    buy_setup = df["buy_setup_count"].values
    sell_setup = df["sell_setup_count"].values

    tdst_buy = np.full(n, np.nan)
    tdst_sell = np.full(n, np.nan)

    current_tdst_buy = np.nan
    current_tdst_sell = np.nan

    # Track setup bar ranges for TDST calculation
    buy_setup_start_idx = -1
    sell_setup_start_idx = -1

    for i in range(n):
        # Track Buy Setup start (when count goes to 1)
        if buy_setup[i] == 1 and (i == 0 or buy_setup[i - 1] != 1):
            buy_setup_start_idx = i

        # Track Sell Setup start (when count goes to 1)
        if sell_setup[i] == 1 and (i == 0 or sell_setup[i - 1] != 1):
            sell_setup_start_idx = i

        # Calculate TDST Buy when Buy Setup 9 completes
        if buy_setup[i] == 9:
            if buy_setup_start_idx >= 0:
                # Lowest low from setup bar 1 to 9
                setup_lows = low[buy_setup_start_idx:i + 1]
                current_tdst_buy = np.min(setup_lows)

        # Calculate TDST Sell when Sell Setup 9 completes
        if sell_setup[i] == 9:
            if sell_setup_start_idx >= 0:
                # Highest high from setup bar 1 to 9
                setup_highs = high[sell_setup_start_idx:i + 1]
                current_tdst_sell = np.max(setup_highs)

        # Invalidate TDST Buy if price breaks below
        if not np.isnan(current_tdst_buy) and low[i] < current_tdst_buy:
            current_tdst_buy = np.nan

        # Invalidate TDST Sell if price breaks above
        if not np.isnan(current_tdst_sell) and high[i] > current_tdst_sell:
            current_tdst_sell = np.nan

        tdst_buy[i] = current_tdst_buy
        tdst_sell[i] = current_tdst_sell

    df["tdst_buy"] = tdst_buy
    df["tdst_sell"] = tdst_sell

    return df


class TDSequentialPlugin(IndicatorPlugin):
    """
    TD Sequential Plugin

    Implements Tom DeMark's TD Sequential indicator including:
    - Setup (1-9): Identifies potential exhaustion points
    - Countdown (1-13): Confirms reversal signals
    - TDST Levels: Support/Resistance levels based on Setup ranges

    Buy Setup: Counts consecutive bars where Close < Close[4]
    Sell Setup: Counts consecutive bars where Close > Close[4]

    Buy Countdown: After Buy Setup 9, counts bars where Close <= Low[2]
    Sell Countdown: After Sell Setup 9, counts bars where Close >= High[2]

    TDST Buy (Support): Lowest low during Buy Setup bars 1-9
    TDST Sell (Resistance): Highest high during Sell Setup bars 1-9
    """

    id = "td_sequential"
    name = "TD Sequential"
    description = "Tom DeMark's TD Sequential with Setup, Countdown and TDST levels"

    def default_config(self) -> Dict[str, Any]:
        return {
            "length_setup": 9,
            "length_countdown": 13,
            "show_setup_numbers": True,
            "show_countdown_numbers": True,
            "show_tdst_levels": True,
        }

    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "length_setup": {
                    "type": "integer",
                    "minimum": 5,
                    "maximum": 15,
                    "title": "Setup Length",
                    "description": "Number of bars for Setup completion (default: 9)"
                },
                "length_countdown": {
                    "type": "integer",
                    "minimum": 8,
                    "maximum": 21,
                    "title": "Countdown Length",
                    "description": "Number of bars for Countdown completion (default: 13)"
                },
                "show_setup_numbers": {
                    "type": "boolean",
                    "title": "Show Setup Numbers",
                    "description": "Display 1-9 count on chart"
                },
                "show_countdown_numbers": {
                    "type": "boolean",
                    "title": "Show Countdown Numbers",
                    "description": "Display 1-13 count on chart"
                },
                "show_tdst_levels": {
                    "type": "boolean",
                    "title": "Show TDST Levels",
                    "description": "Display TDST support/resistance lines"
                },
            }
        }

    def presets(self) -> Dict[str, Dict[str, Any]]:
        """Predefined configurations for different use cases."""
        return {
            "default": {
                "name": "Full TD Sequential",
                "description": "All signals including Setup, Countdown and TDST",
                "config": {
                    "length_setup": 9,
                    "length_countdown": 13,
                    "show_setup_numbers": True,
                    "show_countdown_numbers": True,
                    "show_tdst_levels": True,
                }
            },
            "setup_only": {
                "name": "Setup Only",
                "description": "Only show Setup 1-9 without Countdown",
                "config": {
                    "length_setup": 9,
                    "length_countdown": 13,
                    "show_setup_numbers": True,
                    "show_countdown_numbers": False,
                    "show_tdst_levels": True,
                }
            },
            "tdst_only": {
                "name": "TDST Levels Only",
                "description": "Only show TDST support/resistance levels",
                "config": {
                    "length_setup": 9,
                    "length_countdown": 13,
                    "show_setup_numbers": False,
                    "show_countdown_numbers": False,
                    "show_tdst_levels": True,
                }
            },
        }

    def apply(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Apply TD Sequential calculation to the DataFrame."""
        if df is None or df.empty:
            return df

        length_setup = int(config.get("length_setup", 9))
        length_countdown = int(config.get("length_countdown", 13))

        # The tdsequential library expects uppercase column names (Close, High, Low)
        # Our system uses lowercase, so we need to create temporary uppercase columns
        df = df.copy()

        # Map lowercase to uppercase for the library
        col_mapping = {
            "close": "Close",
            "high": "High",
            "low": "Low",
            "open": "Open",
        }

        for lower, upper in col_mapping.items():
            if lower in df.columns and upper not in df.columns:
                df[upper] = df[lower]

        # Calculate TD Sequential using the library
        df = calculate_td_sequential(
            df,
            close_col="Close",
            high_col="High",
            low_col="Low",
            length_setup=length_setup,
            length_countdown=length_countdown,
        )

        # Calculate TDST levels (requires numeric index)
        # Save original index to restore later
        original_index = df.index.copy()
        df_reset = df.reset_index(drop=True)

        df_reset = calculate_tdst_levels(df_reset, high_col="High", low_col="Low")

        # Restore original index
        df_reset.index = original_index
        df = df_reset

        # Clean up temporary uppercase columns
        for lower, upper in col_mapping.items():
            if upper in df.columns and lower in df.columns:
                df = df.drop(columns=[upper])

        # Create marker columns for each Setup number (1-9)
        # Each column contains: 1.0 for buy setup, -1.0 for sell setup, NaN otherwise
        for i in range(1, length_setup + 1):
            df[f"td_setup_{i}"] = np.where(
                df["buy_setup_count"] == i, 1.0,
                np.where(df["sell_setup_count"] == i, -1.0, np.nan)
            )

        # Create marker columns for each Countdown number (1-13)
        for i in range(1, length_countdown + 1):
            df[f"td_countdown_{i}"] = np.where(
                df["buy_countdown_count"] == i, 1.0,
                np.where(df["sell_countdown_count"] == i, -1.0, np.nan)
            )

        return df

    def chart_series(self, config: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        Define visualization for TD Sequential.

        Includes:
        - TDST support/resistance lines
        - Setup numbers (1-9) markers
        - Countdown numbers (1-13) markers
        """
        cfg = config or self.default_config()
        length_setup = int(cfg.get("length_setup", 9))
        length_countdown = int(cfg.get("length_countdown", 13))
        series = []

        # TDST Support line (green) - Horizontal lines for support levels
        if cfg.get("show_tdst_levels", True):
            series.append({
                "id": "tdst_buy_line",
                "column": "tdst_buy",
                "type": "horizontal_lines",
                "color": "rgba(38, 166, 154, 1)",
                "lineWidth": 2,
                "pane": "main",
            })

            # TDST Resistance line (red) - Horizontal lines for resistance levels
            series.append({
                "id": "tdst_sell_line",
                "column": "tdst_sell",
                "type": "horizontal_lines",
                "color": "rgba(239, 83, 80, 1)",
                "lineWidth": 2,
                "pane": "main",
            })

        # Setup number markers (1-9)
        if cfg.get("show_setup_numbers", True):
            for i in range(1, length_setup + 1):
                is_final = (i == length_setup)
                series.append({
                    "id": f"td_setup_{i}_markers",
                    "type": "markers",
                    "series": "candles",
                    "column": f"td_setup_{i}",
                    # Final 9: bright colors, circle shape with bold text
                    "upColor": "#00ff00" if is_final else "#4dd0e1",
                    "downColor": "#ff0000" if is_final else "#ff8a80",
                    "shapeUp": "circle" if is_final else "text",
                    "shapeDown": "circle" if is_final else "text",
                    # Use larger unicode numbers for 9 to make it stand out
                    "textUp": "⑨" if is_final else str(i),
                    "textDown": "⑨" if is_final else str(i),
                    "pane": "main",
                })

        # Countdown number markers (1-13)
        if cfg.get("show_countdown_numbers", True):
            for i in range(1, length_countdown + 1):
                is_final = (i == length_countdown)
                series.append({
                    "id": f"td_countdown_{i}_markers",
                    "type": "markers",
                    "series": "candles",
                    "column": f"td_countdown_{i}",
                    # Final 13: bright yellow for buy, bright magenta/pink for sell
                    "upColor": "#ffff00" if is_final else "#69f0ae",  # Yellow for buy 13
                    "downColor": "#ff00ff" if is_final else "#ff5252",  # Magenta for sell 13
                    "shapeUp": "arrowUp" if is_final else "text",
                    "shapeDown": "arrowDown" if is_final else "text",
                    "textUp": "13" if is_final else str(i),
                    "textDown": "13" if is_final else str(i),
                    "size": 2 if is_final else 1,  # Larger size for 13
                    "pane": "main",
                })

        return series
