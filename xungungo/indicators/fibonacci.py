"""
Fibonacci Retracement and Extension Plugin

This plugin calculates Fibonacci retracement and extension levels based on
swing highs and lows within a configurable lookback window.

Key Fibonacci Levels:
- 23.6%: Minor retracement, shallow pullback (flags, short pullbacks)
- 38.2%: First significant support/resistance level
- 50.0%: Psychological midpoint (from Dow Theory)
- 61.8%: Golden ratio - most significant level, strong support/resistance
- 78.6%: Deep retracement, significant pullback strength

Extensions (for price targets beyond the swing):
- 127.2%: First extension target
- 161.8%: Golden ratio extension
- 200.0%: Double extension
- 261.8%: Extended target

Usage:
- Combine with other indicators for confirmation (volume, candlesticks, MAs)
- Look for confluence where Fibonacci levels align with other support/resistance
- Use multiple timeframes for stronger signals
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

from .base import IndicatorPlugin

logger = logging.getLogger(__name__)


# Color palette for Fibonacci levels (used in chart rendering)
FIBONACCI_COLORS = {
    0.0: "#808080",      # Gray - swing point
    0.236: "#9C27B0",    # Purple - minor retracement
    0.382: "#2196F3",    # Blue - moderate retracement
    0.5: "#4CAF50",      # Green - midpoint
    0.618: "#FF9800",    # Orange - golden ratio (most important)
    0.786: "#F44336",    # Red - deep retracement
    1.0: "#808080",      # Gray - swing point
    1.272: "#00BCD4",    # Cyan - first extension
    1.414: "#3F51B5",    # Indigo - sqrt(2) extension
    1.618: "#E91E63",    # Pink - golden extension
    2.0: "#795548",      # Brown - double extension
    2.618: "#607D8B",    # Blue Gray - extended target
}


def _safe_float_series(df: pd.DataFrame, col: str) -> np.ndarray:
    """Safely extract a column as float numpy array."""
    if col not in df.columns:
        return np.array([], dtype=float)
    return df[col].astype(float).to_numpy()


def _find_swing_points(
    highs: np.ndarray, lows: np.ndarray
) -> Tuple[Optional[int], Optional[int], Optional[float], Optional[float]]:
    """
    Find swing high and low indices and values, handling all-NaN cases.

    Returns:
        Tuple of (hi_idx, lo_idx, swing_high, swing_low) or (None, None, None, None) if invalid
    """
    # Check for all-NaN or empty arrays
    if highs.size == 0 or lows.size == 0:
        return None, None, None, None

    # Check if all values are NaN
    if np.all(np.isnan(highs)) or np.all(np.isnan(lows)):
        logger.warning("Fibonacci: All values are NaN, cannot compute swing points")
        return None, None, None, None

    try:
        hi_idx = int(np.nanargmax(highs))
        lo_idx = int(np.nanargmin(lows))
        swing_high = float(highs[hi_idx])
        swing_low = float(lows[lo_idx])

        # Validate the values are finite
        if not np.isfinite(swing_high) or not np.isfinite(swing_low):
            logger.warning("Fibonacci: Swing points are not finite")
            return None, None, None, None

        return hi_idx, lo_idx, swing_high, swing_low

    except ValueError as e:
        # This catches the "All-NaN slice encountered" error
        logger.warning(f"Fibonacci: Could not find swing points: {e}")
        return None, None, None, None


def _fib_levels(low: float, high: float, ratios: List[float]) -> Dict[float, float]:
    """
    Calculate Fibonacci retracement levels for a DOWN swing (high -> low).

    Returns a dict mapping ratio -> price level, where:
      - ratio=0.0 => high (start of retracement)
      - ratio=1.0 => low (end of retracement)
      - ratio>1.0 => extension below low
    """
    span = high - low
    return {r: high - span * r for r in ratios}


def _fib_levels_up(low: float, high: float, ratios: List[float]) -> Dict[float, float]:
    """
    Calculate Fibonacci retracement levels for an UP swing (low -> high).

    Returns a dict mapping ratio -> price level, where:
      - ratio=0.0 => low (start of retracement)
      - ratio=1.0 => high (end of retracement)
      - ratio>1.0 => extension above high
    """
    span = high - low
    return {r: low + span * r for r in ratios}


def _to_float_list(x: Any, name: str = "ratios") -> List[float]:
    """
    Sanitize a list of values to floats, logging any invalid entries.
    """
    if not isinstance(x, (list, tuple)):
        logger.warning(f"Fibonacci: {name} is not a list, using empty list")
        return []

    out = []
    for i, v in enumerate(x):
        try:
            out.append(float(v))
        except (ValueError, TypeError) as e:
            logger.warning(f"Fibonacci: Invalid {name}[{i}]={v!r}, skipping: {e}")
    return out


def _ratio_to_col(ratio: float, prefix: str, round_digits: int) -> str:
    """
    Convert a ratio to a stable column name.

    Examples:
        0.618 -> fib_0_618
        1.272 -> fib_1_272
        -0.5 -> fib_m0_5 (negative)
    """
    r = round(ratio, round_digits)
    s = str(r).replace(".", "_").replace("-", "m")
    return f"{prefix}_{s}"


def _determine_direction(
    mode: str, hi_idx: int, lo_idx: int, swing_high: float, swing_low: float
) -> Optional[str]:
    """
    Determine the swing direction based on mode and indices.

    Returns:
        "up", "down", or None if direction cannot be determined
    """
    mode = mode.lower().strip()

    if mode in ("up", "down"):
        return mode

    # Auto mode: determine by which extreme occurs last
    if mode == "auto":
        if hi_idx > lo_idx:
            # High occurred after low -> upswing (low to high)
            return "up"
        elif lo_idx > hi_idx:
            # Low occurred after high -> downswing (high to low)
            return "down"
        else:
            # Same index - need additional logic
            # This happens when high and low occur at the same bar
            # Use price range to determine: if we're closer to high, trend was up
            if swing_high == swing_low:
                logger.warning("Fibonacci: swing_high equals swing_low, cannot determine direction")
                return None
            # Default to down for ambiguous cases (more conservative)
            logger.debug("Fibonacci: hi_idx == lo_idx, defaulting to 'down'")
            return "down"

    # Unknown mode, default to down
    logger.warning(f"Fibonacci: Unknown mode '{mode}', defaulting to 'down'")
    return "down"


class FibonacciPlugin(IndicatorPlugin):
    """
    Fibonacci Retracement and Extension Plugin.

    Calculates Fibonacci levels based on swing highs/lows within a lookback window.
    Supports automatic direction detection, configurable ratios, and extensions.
    """

    id = "fibonacci"
    name = "Fibonacci"
    description = "Fibonacci retracement and extension levels for support/resistance analysis."

    def default_config(self) -> Dict[str, Any]:
        return {
            "mode": "auto",           # "auto" | "down" | "up"
            "lookback": 200,          # bars to consider to find swing high/low
            "high_col": "high",       # column used to find swing high
            "low_col": "low",         # column used to find swing low
            "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
            "extensions": [1.272, 1.618],  # extension levels beyond retracement
            "prefix": "fib",          # column prefix, e.g. fib_0_618
            "round": 6,               # decimals for column naming
            "show_levels": [0.236, 0.382, 0.5, 0.618, 0.786],  # levels to show in chart
        }

    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["auto", "down", "up"],
                    "title": "Mode",
                    "description": (
                        "auto: infer direction by which extreme happens last; "
                        "down: high->low retracement; up: low->high retracement"
                    ),
                },
                "lookback": {
                    "type": "integer",
                    "minimum": 10,
                    "maximum": 1000,
                    "format": "slider",
                    "title": "Lookback",
                    "description": "Number of bars to analyze for swing detection",
                },
                "high_col": {"type": "string", "enum": ["high"], "title": "High column"},
                "low_col": {"type": "string", "enum": ["low"], "title": "Low column"},
                "ratios": {
                    "type": "array",
                    "items": {"type": "number", "minimum": 0, "maximum": 1},
                    "title": "Retracement ratios",
                    "description": "Fibonacci ratios between 0 and 1 for retracement levels",
                },
                "extensions": {
                    "type": "array",
                    "items": {"type": "number", "minimum": 1},
                    "title": "Extensions",
                    "description": "Fibonacci ratios > 1 for extension levels",
                },
                "prefix": {"type": "string", "title": "Prefix"},
                "round": {"type": "integer", "minimum": 0, "maximum": 12, "title": "Rounding"},
                "show_levels": {
                    "type": "array",
                    "items": {"type": "number"},
                    "title": "Show Levels",
                    "description": "Which levels to display in the chart",
                },
            },
        }

    def presets(self) -> Dict[str, Dict[str, Any]]:
        """Predefined configurations for different Fibonacci setups."""
        return {
            "default": {
                "name": "Default Auto",
                "description": "Automatic direction detection with standard ratios and key extensions",
                "config": {
                    "mode": "auto",
                    "lookback": 200,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
                    "extensions": [1.272, 1.618],
                    "prefix": "fib",
                    "round": 6,
                    "show_levels": [0.236, 0.382, 0.5, 0.618, 0.786],
                }
            },
            "golden_ratio": {
                "name": "Golden Ratio Focus",
                "description": "Focus on the most significant levels (38.2%, 50%, 61.8%)",
                "config": {
                    "mode": "auto",
                    "lookback": 200,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.382, 0.5, 0.618],
                    "extensions": [1.618],
                    "prefix": "fib",
                    "round": 6,
                    "show_levels": [0.382, 0.5, 0.618, 1.618],
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
                    "show_levels": [0.236, 0.382, 0.5, 0.618, 0.786],
                }
            },
            "short_term": {
                "name": "Short Term (Day Trading)",
                "description": "Shorter lookback (50 bars) for intraday analysis",
                "config": {
                    "mode": "auto",
                    "lookback": 50,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
                    "extensions": [1.272, 1.618],
                    "prefix": "fib",
                    "round": 6,
                    "show_levels": [0.382, 0.5, 0.618],
                }
            },
            "long_term": {
                "name": "Long Term (Swing Trading)",
                "description": "Extended lookback (500 bars) for swing trading analysis",
                "config": {
                    "mode": "auto",
                    "lookback": 500,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
                    "extensions": [1.272, 1.618],
                    "prefix": "fib",
                    "round": 6,
                    "show_levels": [0.236, 0.382, 0.5, 0.618, 0.786],
                }
            },
            "extended_targets": {
                "name": "Extended Targets",
                "description": "Include all extension levels for price targets",
                "config": {
                    "mode": "auto",
                    "lookback": 200,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
                    "extensions": [1.272, 1.414, 1.618, 2.0, 2.618],
                    "prefix": "fib",
                    "round": 6,
                    "show_levels": [0.382, 0.5, 0.618, 1.272, 1.618, 2.618],
                }
            },
            "all_levels": {
                "name": "All Levels",
                "description": "Display all retracement and extension levels",
                "config": {
                    "mode": "auto",
                    "lookback": 200,
                    "high_col": "high",
                    "low_col": "low",
                    "ratios": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
                    "extensions": [1.272, 1.414, 1.618, 2.0, 2.618],
                    "prefix": "fib",
                    "round": 6,
                    "show_levels": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618],
                }
            }
        }

    def apply(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply Fibonacci analysis to the dataframe.

        Calculates swing points within the lookback window and computes
        retracement and extension levels.
        """
        if df is None or df.empty:
            return df

        high_col = str(config.get("high_col", "high"))
        low_col = str(config.get("low_col", "low"))

        if high_col not in df.columns or low_col not in df.columns:
            logger.warning(f"Fibonacci: Required columns {high_col}/{low_col} not found")
            return df

        # Get configuration with validation
        lookback_requested = int(config.get("lookback", 200))
        lookback = max(5, min(lookback_requested, len(df)))

        if lookback != lookback_requested:
            logger.info(
                f"Fibonacci: Lookback adjusted from {lookback_requested} to {lookback} "
                f"(data has {len(df)} rows)"
            )

        prefix = str(config.get("prefix", "fib"))
        rnd = int(config.get("round", 6))
        mode = str(config.get("mode", "auto"))

        # Sanitize ratios and extensions
        ratios_raw = config.get("ratios", [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0])
        extensions_raw = config.get("extensions", [1.272, 1.618])

        ratios_f = _to_float_list(ratios_raw, "ratios")
        exts_f = [r for r in _to_float_list(extensions_raw, "extensions") if r > 1.0]

        if not ratios_f:
            logger.warning("Fibonacci: No valid ratios provided, using defaults")
            ratios_f = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

        # Extract window for swing analysis
        window = df.iloc[-lookback:].copy()
        highs = _safe_float_series(window, high_col)
        lows = _safe_float_series(window, low_col)

        # Find swing points with proper error handling
        hi_idx, lo_idx, swing_high, swing_low = _find_swing_points(highs, lows)

        if hi_idx is None or swing_high is None or swing_low is None:
            logger.warning("Fibonacci: Could not determine swing points")
            return df

        # Validate swing range
        if swing_high <= swing_low:
            logger.warning(
                f"Fibonacci: Invalid swing range (high={swing_high}, low={swing_low})"
            )
            return df

        # Determine direction
        direction = _determine_direction(mode, hi_idx, lo_idx, swing_high, swing_low)
        if direction is None:
            return df

        # Compute all levels (retracements + extensions)
        all_ratios = sorted(set(ratios_f + exts_f))

        if direction == "down":
            levels = _fib_levels(low=swing_low, high=swing_high, ratios=all_ratios)
        else:
            levels = _fib_levels_up(low=swing_low, high=swing_high, ratios=all_ratios)

        # Build output dataframe
        out = df.copy()

        # Store metadata columns
        out[f"{prefix}_dir"] = direction
        out[f"{prefix}_swing_high"] = swing_high
        out[f"{prefix}_swing_low"] = swing_low
        out[f"{prefix}_lookback"] = lookback
        out[f"{prefix}_lookback_requested"] = lookback_requested
        out[f"{prefix}_span"] = swing_high - swing_low
        out[f"{prefix}_span_pct"] = ((swing_high - swing_low) / swing_low) * 100

        # Store each level as a column
        for ratio, price in levels.items():
            col_name = _ratio_to_col(ratio, prefix, rnd)
            out[col_name] = float(price)

        return out

    def chart_series(self, config: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        Generate chart series configuration for Fibonacci levels.

        Uses the fibonacci_levels type which renders horizontal lines with labels
        directly on the chart, similar to TradingView's Fibonacci tool.
        """
        cfg = config or self.default_config()
        prefix = cfg.get("prefix", "fib")
        rnd = int(cfg.get("round", 6))

        # Get levels to show (default to key levels if not specified)
        show_levels = cfg.get("show_levels", [0.236, 0.382, 0.5, 0.618, 0.786])

        if not isinstance(show_levels, list):
            show_levels = [0.382, 0.5, 0.618]

        # Build the levels array for the fibonacci_levels primitive
        levels = []
        columns_needed = []

        for level in show_levels:
            try:
                ratio = float(level)
                col_name = _ratio_to_col(ratio, prefix, rnd)
                columns_needed.append(col_name)

                # Get color for this level (or default gray)
                color = FIBONACCI_COLORS.get(ratio, "#888888")

                # Format label for display
                if ratio == 0.0:
                    label = "0%"
                elif ratio == 1.0:
                    label = "100%"
                elif ratio <= 1:
                    label = f"{ratio:.1%}"
                else:
                    label = f"{ratio:.1%}"

                levels.append({
                    "ratio": ratio,
                    "column": col_name,
                    "color": color,
                    "label": label,
                    "lineWidth": 1 if ratio in (0.0, 1.0) else 2,
                    "lineStyle": 0 if ratio <= 1 else 2,  # 0=solid, 2=dashed for extensions
                })
            except (ValueError, TypeError):
                continue

        if not levels:
            return []

        # Return a single fibonacci_levels series that contains all levels
        # This is more efficient than creating multiple line series
        return [
            {
                "id": f"{prefix}_levels",
                "type": "fibonacci_levels",
                "levels": levels,
                "columns": columns_needed,  # For data extraction
                "showLabels": True,
                "labelPosition": "right",
                "pane": "main",
            }
        ]
