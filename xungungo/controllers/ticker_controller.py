from __future__ import annotations
import json
import re
import pandas as pd
from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool

from xungungo.core.logger import get_logger
from xungungo.data.datasource_base import DataSource
from xungungo.indicators.manager import PluginManager
from xungungo.bridge.chart_bridge import ChartBridge

# Valid ticker symbol pattern (alphanumeric, dash, dot, equals, optional leading caret)
VALID_SYMBOL_PATTERN = re.compile(r'^\^?[A-Z0-9\-\.=]+$', re.IGNORECASE)

class _WorkerSignals(QObject):
    done = Signal(object)
    error = Signal(str)

class _FetchComputeTask(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = _WorkerSignals()

    def run(self):
        try:
            res = self.fn()
            self.signals.done.emit(res)
        except Exception as e:
            self.signals.error.emit(str(e))

class TickerController(QObject):
    statusChanged = Signal(str)
    pluginsChanged = Signal(str)  # JSON list

    def __init__(self, datasource: DataSource, plugins: PluginManager, bridge: ChartBridge):
        super().__init__()
        self.log = get_logger("xungungo.ticker")
        self.datasource = datasource
        self.plugins = plugins
        self.bridge = bridge

        self.df_main: pd.DataFrame | None = None
        self.symbol: str | None = None
        self.interval: str = "1d"
        self.period: str = "10y"

        self.pool = QThreadPool.globalInstance()

    @Slot(result=str)
    def getPlugins(self) -> str:
        return json.dumps(self.plugins.list_plugins())

    @Slot(str, result=str)
    def getPluginConfig(self, plugin_id: str) -> str:
        """Get the current configuration for a plugin as JSON string"""
        try:
            cfg = self.plugins.get_config(plugin_id)
            return json.dumps(cfg)
        except Exception as e:
            self.log.error(f"Error getting config for {plugin_id}: {e}")
            return "{}"

    @Slot(str, bool)
    def setPluginEnabled(self, plugin_id: str, enabled: bool):
        self.plugins.enable(plugin_id, enabled)
        self.pluginsChanged.emit(self.getPlugins())
        if self.df_main is not None:
            self._recompute_and_push()
        self._save_current_state()

    @Slot(str, float, float)
    def setKalmanParams(self, plugin_id: str, fast_q: float, slow_q: float):
        # update nested config (simple)
        cfg = self.plugins.get_config(plugin_id)
        fast = cfg.get("fast", {}).copy()
        slow = cfg.get("slow", {}).copy()
        fast["process_variance"] = float(fast_q)
        slow["process_variance"] = float(slow_q)
        cfg["fast"] = fast
        cfg["slow"] = slow
        self.plugins.set_config(plugin_id, cfg)
        self.pluginsChanged.emit(self.getPlugins())
        if self.df_main is not None and plugin_id in self.plugins.enabled_plugins():
            self._recompute_and_push()

    @staticmethod
    def _deep_merge(base: dict, patch: dict) -> dict:
        out = base.copy()
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(out.get(key), dict):
                out[key] = TickerController._deep_merge(out[key], value)
            else:
                out[key] = value
        return out

    @Slot(str, str)
    def setPluginConfig(self, plugin_id: str, patch_json: str):
        try:
            patch = json.loads(patch_json or "{}")
        except Exception as e:
            self.log.error(f"Invalid config patch for {plugin_id}: {e}")
            return
        if not isinstance(patch, dict):
            self.log.error(f"Config patch for {plugin_id} must be a JSON object")
            return
        cfg = self.plugins.get_config(plugin_id)
        cfg = self._deep_merge(cfg, patch)
        self.plugins.set_config(plugin_id, cfg)
        self.pluginsChanged.emit(self.getPlugins())
        if self.df_main is not None and plugin_id in self.plugins.enabled_plugins():
            self._recompute_and_push()
        self._save_current_state()

    @Slot(str, str, result=bool)
    def applyPreset(self, plugin_id: str, preset_id: str) -> bool:
        """Apply a preset to a plugin's configuration"""
        success = self.plugins.apply_preset(plugin_id, preset_id)
        if success:
            self.pluginsChanged.emit(self.getPlugins())
            if self.df_main is not None and plugin_id in self.plugins.enabled_plugins():
                self._recompute_and_push()
            self._save_current_state()
        return success

    @Slot(str, str, str, str, str, result=bool)
    def addCustomPreset(self, plugin_id: str, preset_id: str, name: str, description: str, config_json: str) -> bool:
        """Add a custom preset for a plugin"""
        try:
            config = json.loads(config_json or "{}")
        except Exception as e:
            self.log.error(f"Invalid config JSON for custom preset: {e}")
            return False

        success = self.plugins.add_custom_preset(plugin_id, preset_id, name, description, config)
        if success:
            self.pluginsChanged.emit(self.getPlugins())
        return success

    @Slot(str, str, result=bool)
    def deleteCustomPreset(self, plugin_id: str, preset_id: str) -> bool:
        """Delete a custom preset"""
        success = self.plugins.delete_custom_preset(plugin_id, preset_id)
        if success:
            self.pluginsChanged.emit(self.getPlugins())
        return success

    @Slot(str)
    def loadSymbol(self, symbol: str):
        symbol = (symbol or "").strip().upper()
        if not symbol:
            return

        # Validate symbol format to prevent injection attacks
        if not VALID_SYMBOL_PATTERN.match(symbol):
            self.statusChanged.emit(
                f"Error: Simbolo invalido '{symbol}'. Use solo letras, numeros, guiones, puntos y '^' al inicio."
            )
            return

        # Save current ticker state before switching
        if self.symbol:
            self._save_current_state()

        self.symbol = symbol

        # Try to load saved state for this ticker
        saved_state = self.plugins.load_chart_state_for_ticker(symbol)
        if saved_state:
            self.interval = saved_state.get("interval", self.interval)
            self.period = saved_state.get("period", self.period)
            self.plugins.apply_chart_state(saved_state)
            self.pluginsChanged.emit(self.getPlugins())
            self.log.info(f"Restored saved state for {symbol}")

        self._reload_symbol()

    @Slot(result=str)
    def getInterval(self) -> str:
        return self.interval

    @Slot(result=str)
    def getPeriod(self) -> str:
        return self.period

    @Slot(str)
    def setInterval(self, interval: str):
        interval = (interval or "").strip()
        if not interval:
            return
        interval, period = self.datasource.normalize_interval_period(interval, self.period)
        if interval == self.interval and period == self.period:
            return
        self.interval = interval
        self.period = period
        if self.symbol:
            self._reload_symbol()
            self._save_current_state()

    @Slot(str)
    def setPeriod(self, period: str):
        period = (period or "").strip()
        if not period:
            return
        interval, period = self.datasource.normalize_interval_period(self.interval, period)
        if interval == self.interval and period == self.period:
            return
        self.interval = interval
        self.period = period
        if self.symbol:
            self._reload_symbol()
            self._save_current_state()

    def _reload_symbol(self):
        if not self.symbol:
            return
        symbol = self.symbol
        interval, period = self.datasource.normalize_interval_period(self.interval, self.period)
        self.interval = interval
        self.period = period
        self.statusChanged.emit(f"Cargando {symbol} ({self.interval}/{self.period})...")
        def job():
            df = self.datasource.fetch_ohlcv(symbol, interval=self.interval, period=self.period)
            df2 = self.plugins.compute_all(df)
            return df2
        task = _FetchComputeTask(job)
        task.signals.done.connect(self._on_loaded)
        task.signals.error.connect(self._on_error)
        self.pool.start(task)

    def _on_loaded(self, df: pd.DataFrame):
        self.df_main = df
        self.statusChanged.emit(f"OK: {self.symbol} ({len(df)} velas)")
        self._push_all()

    def _on_error(self, msg: str):
        self.statusChanged.emit(f"Error: {msg}")

    def _recompute_and_push(self):
        if self.df_main is None:
            return
        # recompute from base OHLCV (drop indicator cols)
        base_cols = ["timestamp","open","high","low","close","volume"]
        df_base = self.df_main[base_cols].copy()
        df2 = self.plugins.compute_all(df_base)
        self.df_main = df2
        self._push_indicators_only()

    def _to_epoch(self, ts):
        # ts is pandas Timestamp (tz-aware)
        return int(pd.Timestamp(ts).timestamp())

    def _get_series_definitions(self):
        """
        Collect all series definitions from enabled plugins.
        Returns list of dicts describing how to render each series.
        """
        series_defs = []

        for pid in self.plugins.enabled_plugins():
            plugin = self.plugins.get_plugin(pid)
            if not plugin:
                continue

            # Get current configuration for this plugin
            cfg = self.plugins.get_config(pid)

            # Get series definitions from plugin (with config for dynamic series)
            defs = plugin.chart_series(cfg)
            if defs:
                series_defs.extend(defs)

        return series_defs

    def _push_all(self):
        if self.df_main is None:
            return
        df = self.df_main

        # Optimized: Use itertuples instead of zip for 3-5x better performance
        candles = [
            {
                "time": self._to_epoch(row.timestamp),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
            }
            for row in df[["timestamp", "open", "high", "low", "close"]].itertuples(index=False)
        ]
        
        indicators = self._build_indicator_data(df)
        series_defs = self._get_series_definitions()
        
        payload = {
            "type": "all",
            "candles": candles,
            "indicators": indicators,
            "seriesDefs": series_defs
        }
        self.bridge.push.emit(json.dumps(payload))

    def _push_indicators_only(self):
        if self.df_main is None:
            return
        df = self.df_main
        
        indicators = self._build_indicator_data(df)
        series_defs = self._get_series_definitions()
        
        payload = {
            "type": "indicators",
            "indicators": indicators,
            "seriesDefs": series_defs
        }
        self.bridge.push.emit(json.dumps(payload))

    def _build_indicator_data(self, df: pd.DataFrame):
        """
        Build indicator data dict.
        Key = column name, Value = list of {time, value} points
        """
        out = {}

        # Collect all columns that need to be sent
        columns_needed = set()

        for pid in self.plugins.enabled_plugins():
            plugin = self.plugins.get_plugin(pid)
            if not plugin:
                continue

            # CRITICAL FIX: Pass current configuration to chart_series()
            cfg = self.plugins.get_config(pid)

            for s in plugin.chart_series(cfg):
                # Series with direct column data (line, markers, etc.)
                if s.get("column"):
                    columns_needed.add(s.get("column"))

                # Band series (upper/lower columns)
                if s.get("type") == "band":
                    if s.get("upperColumn"):
                        columns_needed.add(s.get("upperColumn"))
                    if s.get("lowerColumn"):
                        columns_needed.add(s.get("lowerColumn"))

        # Build data for each column
        for col in columns_needed:
            if col in df.columns:
                out[col] = [
                    {"time": self._to_epoch(t), "value": float(v)}
                    for t, v in zip(df["timestamp"], df[col])
                    if pd.notna(v)  # Skip NaN values
                ]

        return out

    def _save_current_state(self) -> None:
        """Save current chart state for the current ticker."""
        if self.symbol:
            self.plugins.save_chart_state_for_ticker(
                self.symbol, self.interval, self.period
            )

    @Slot(result=str)
    def getChartState(self) -> str:
        """Get saved chart state for current ticker (for QML to sync UI)."""
        if not self.symbol:
            return "{}"
        state = self.plugins.load_chart_state_for_ticker(self.symbol)
        if state:
            return json.dumps({
                "interval": state.get("interval", self.interval),
                "period": state.get("period", self.period)
            })
        return json.dumps({
            "interval": self.interval,
            "period": self.period
        })
