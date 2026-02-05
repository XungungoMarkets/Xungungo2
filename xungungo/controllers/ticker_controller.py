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


class TabState:
    """Encapsula el estado de un tab individual."""
    def __init__(self):
        self.symbol: str | None = None
        self.interval: str = "1d"
        self.period: str = "10y"
        self.df_main: pd.DataFrame | None = None
        self.bridge: ChartBridge | None = None
        # Plugin state for this tab (what plugins are enabled and their config)
        self.plugin_state: dict | None = None
        # Track if plugins UI was initialized for this tab
        self.plugins_ui_initialized: bool = False
        # Track if bridge signals are connected to avoid duplicates
        self.bridge_connected: bool = False
        # Track pending load job to cancel duplicates
        self.pending_load_id: int = 0

class _WorkerSignals(QObject):
    done = Signal(object)
    error = Signal(str, str)  # (tab_id, message)

class _FetchComputeTask(QRunnable):
    def __init__(self, fn, tab_id, plugin_state=None):
        super().__init__()
        self.fn = fn
        self.tab_id = tab_id
        self.plugin_state = plugin_state
        self.signals = _WorkerSignals()

    def run(self):
        try:
            res = self.fn()
            self.signals.done.emit((res, self.tab_id))
        except Exception as e:
            self.signals.error.emit(self.tab_id, str(e))

class TickerController(QObject):
    statusChanged = Signal(str, str)  # (tab_id, message)
    pluginsChanged = Signal(str, str)  # (tab_id, JSON list)

    def __init__(self, datasource: DataSource, plugins: PluginManager):
        super().__init__()
        self.log = get_logger("xungungo.ticker")
        self.datasource = datasource
        self.plugins = plugins

        # Multi-tab support: estado por tab
        self._tab_states: dict[str, TabState] = {}
        self._current_tab_id: str | None = None

        self.pool = QThreadPool.globalInstance()

    def _get_current_state(self) -> TabState:
        """Retorna el estado del tab actual."""
        if self._current_tab_id and self._current_tab_id in self._tab_states:
            return self._tab_states[self._current_tab_id]
        # Fallback: crear estado temporal
        if self._current_tab_id:
            self._tab_states[self._current_tab_id] = TabState()
            return self._tab_states[self._current_tab_id]
        # Si no hay tab activo, crear uno temporal
        temp_state = TabState()
        return temp_state

    @Slot(str)
    def setCurrentTab(self, tab_id: str):
        """Cambia el tab activo."""
        # Save current tab's plugin state before switching
        if self._current_tab_id and self._current_tab_id in self._tab_states:
            current_state = self._tab_states[self._current_tab_id]
            current_state.plugin_state = self.plugins.get_state_snapshot()
            self.log.debug(f"Saved plugin state for tab: {self._current_tab_id}")

        # Create new tab state if needed
        if tab_id not in self._tab_states:
            self._tab_states[tab_id] = TabState()

        # Switch to new tab
        self._current_tab_id = tab_id
        self.log.debug(f"Current tab changed to: {tab_id}")

        # Restore new tab's plugin state
        state = self._get_current_state()
        if state.plugin_state:
            self.plugins.restore_state_snapshot(state.plugin_state)
            self.log.debug(f"Restored plugin state for tab: {tab_id}")

        # Emit status for UI sync
        if state.symbol:
            self.statusChanged.emit(tab_id, f"OK: {state.symbol} ({len(state.df_main) if state.df_main is not None else 0} velas)")
            # Re-push data to chart if already loaded
            if state.df_main is not None and state.bridge is not None:
                self._push_all()

        # Only emit pluginsChanged on first visit to avoid UI rebuilds
        if not state.plugins_ui_initialized:
            state.plugins_ui_initialized = True
            self.pluginsChanged.emit(tab_id, self.getPlugins())

    @Slot(str, QObject)
    def connectBridge(self, tab_id: str, proxy: QObject):
        """Conecta un bridge a un proxy QML."""
        if tab_id not in self._tab_states:
            self._tab_states[tab_id] = TabState()

        state = self._tab_states[tab_id]

        # Crear bridge para este tab si no existe
        if state.bridge is None:
            state.bridge = ChartBridge(parent=self)
            self.log.info(f"Bridge created for tab: {tab_id}, bridge_id={id(state.bridge)}")

        # Avoid duplicate signal connections
        if state.bridge_connected:
            self.log.debug(f"Bridge already connected for tab: {tab_id}, skipping")
            return

        # Conectar bridge a proxy
        bridge = state.bridge
        try:
            bridge.push.connect(proxy.push)
            # When bridge is ready, push data if already loaded
            proxy.readyRequested.connect(lambda tid=tab_id: self._on_bridge_ready(tid))
            proxy.readyRequested.connect(bridge.ready)
            state.bridge_connected = True
            self.log.info(f"Bridge connected for tab: {tab_id}, bridge_id={id(bridge)}, proxy={proxy.objectName()}")
        except Exception as e:
            self.log.error(f"Failed to connect bridge for {tab_id}: {e}")

    def _on_bridge_ready(self, tab_id: str):
        """Called when a bridge signals it's ready."""
        self.log.info(f"_on_bridge_ready: tab_id={tab_id}")
        if tab_id in self._tab_states:
            state = self._tab_states[tab_id]
            self.log.info(f"_on_bridge_ready: tab={tab_id}, symbol={state.symbol}, has_data={state.df_main is not None}, bridge_id={id(state.bridge) if state.bridge else None}")
            # If this tab already has data loaded, push it now
            if state.df_main is not None and state.bridge is not None:
                self.log.info(f"_on_bridge_ready: Re-pushing data for tab {tab_id}, symbol={state.symbol}")
                self._push_all_for_tab(tab_id)
        else:
            self.log.warning(f"_on_bridge_ready: tab_id={tab_id} not in _tab_states!")

    @Slot(str, result=str)
    def getBridgeForTab(self, tab_id: str) -> str:
        """Retorna el objectName del bridge para un tab (usado internamente)."""
        if tab_id in self._tab_states and self._tab_states[tab_id].bridge:
            return self._tab_states[tab_id].bridge.objectName()
        return ""

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
        if self._current_tab_id:
            self.pluginsChanged.emit(self._current_tab_id, self.getPlugins())
        state = self._get_current_state()
        # CRITICAL: Update tab's plugin_state before saving so changes persist
        state.plugin_state = self.plugins.get_state_snapshot()
        if state.df_main is not None:
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
        if self._current_tab_id:
            self.pluginsChanged.emit(self._current_tab_id, self.getPlugins())
        state = self._get_current_state()
        if state.df_main is not None and plugin_id in self.plugins.enabled_plugins():
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
        if self._current_tab_id:
            self.pluginsChanged.emit(self._current_tab_id, self.getPlugins())
        state = self._get_current_state()
        # CRITICAL: Update tab's plugin_state before saving so changes persist
        state.plugin_state = self.plugins.get_state_snapshot()
        if state.df_main is not None and plugin_id in self.plugins.enabled_plugins():
            self._recompute_and_push()
        self._save_current_state()

    @Slot(str, str, result=bool)
    def applyPreset(self, plugin_id: str, preset_id: str) -> bool:
        """Apply a preset to a plugin's configuration"""
        success = self.plugins.apply_preset(plugin_id, preset_id)
        if success and self._current_tab_id:
            self.pluginsChanged.emit(self._current_tab_id, self.getPlugins())
            state = self._get_current_state()
            # CRITICAL: Update tab's plugin_state before saving so changes persist
            state.plugin_state = self.plugins.get_state_snapshot()
            if state.df_main is not None and plugin_id in self.plugins.enabled_plugins():
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
        if success and self._current_tab_id:
            self.pluginsChanged.emit(self._current_tab_id, self.getPlugins())
        return success

    @Slot(str, str, result=bool)
    def deleteCustomPreset(self, plugin_id: str, preset_id: str) -> bool:
        """Delete a custom preset"""
        success = self.plugins.delete_custom_preset(plugin_id, preset_id)
        if success and self._current_tab_id:
            self.pluginsChanged.emit(self._current_tab_id, self.getPlugins())
        return success

    @Slot(str, str)
    def loadSymbolForTab(self, tab_id: str, symbol: str):
        """Load a symbol for a specific tab (thread-safe for concurrent loads)."""
        symbol = (symbol or "").strip().upper()
        if not symbol or not tab_id:
            return

        # Validate symbol format to prevent injection attacks
        if not VALID_SYMBOL_PATTERN.match(symbol):
            self.statusChanged.emit(
                tab_id,
                f"Error: Simbolo invalido '{symbol}'. Use solo letras, numeros, guiones, puntos y '^' al inicio."
            )
            return

        # Ensure tab state exists
        if tab_id not in self._tab_states:
            self._tab_states[tab_id] = TabState()

        state = self._tab_states[tab_id]

        # Save current ticker state before switching
        if state.symbol:
            self._save_state_for_tab(tab_id)

        state.symbol = symbol

        # Try to load saved state for this ticker
        saved_state = self.plugins.load_chart_state_for_ticker(symbol)
        if saved_state:
            state.interval = saved_state.get("interval", state.interval)
            state.period = saved_state.get("period", state.period)
            # Save the chart state to the tab's plugin_state
            state.plugin_state = {
                "enabled": {pid: ind.get("enabled", False) for pid, ind in saved_state.get("indicators", {}).items()},
                "configs": {pid: ind.get("config", {}) for pid, ind in saved_state.get("indicators", {}).items()},
                "preset_ids": {pid: ind.get("preset_id", "") for pid, ind in saved_state.get("indicators", {}).items()}
            }
            # Debug: log what we're restoring
            enabled_plugins = [pid for pid, en in state.plugin_state["enabled"].items() if en]
            self.log.info(f"Restoring state for {symbol}: enabled_plugins={enabled_plugins}")
            # Apply restored state to global PluginManager so UI reflects it
            self.plugins.restore_state_snapshot(state.plugin_state)
            # Debug: verify state was applied
            global_enabled = self.plugins.enabled_plugins()
            self.log.info(f"After restore: global_enabled={global_enabled}")
            self.log.info(f"Restored saved state for {symbol} in tab {tab_id}")
            # Emit pluginsChanged to update UI with restored indicators
            self.pluginsChanged.emit(tab_id, self.getPlugins())

        self._reload_symbol_for_tab(tab_id)

    @Slot(str)
    def loadSymbol(self, symbol: str):
        """Load a symbol for the current tab (legacy API)."""
        if self._current_tab_id:
            self.loadSymbolForTab(self._current_tab_id, symbol)
        else:
            self.log.warning("loadSymbol called without current tab set")

    @Slot(result=str)
    def getInterval(self) -> str:
        state = self._get_current_state()
        return state.interval

    @Slot(result=str)
    def getPeriod(self) -> str:
        state = self._get_current_state()
        return state.period

    @Slot(str, result=str)
    def getIntervalForTab(self, tab_id: str) -> str:
        """Get interval for a specific tab."""
        if tab_id in self._tab_states:
            return self._tab_states[tab_id].interval
        return "1d"

    @Slot(str, result=str)
    def getPeriodForTab(self, tab_id: str) -> str:
        """Get period for a specific tab."""
        if tab_id in self._tab_states:
            return self._tab_states[tab_id].period
        return "1y"

    @Slot(str)
    def setInterval(self, interval: str):
        interval = (interval or "").strip()
        if not interval:
            return
        state = self._get_current_state()
        interval, period = self.datasource.normalize_interval_period(interval, state.period)
        if interval == state.interval and period == state.period:
            return
        state.interval = interval
        state.period = period
        if state.symbol:
            self._reload_symbol()
            self._save_current_state()

    @Slot(str)
    def setPeriod(self, period: str):
        period = (period or "").strip()
        if not period:
            return
        state = self._get_current_state()
        # Use normalize_period_adjusting_interval to adjust interval UP if period requires it
        interval, period = self.datasource.normalize_period_adjusting_interval(state.interval, period)
        if interval == state.interval and period == state.period:
            return
        state.interval = interval
        state.period = period
        if state.symbol:
            self._reload_symbol()
            self._save_current_state()

    def _reload_symbol_for_tab(self, tab_id: str):
        """Reload symbol data for a specific tab (thread-safe)."""
        if tab_id not in self._tab_states:
            self.log.warning(f"_reload_symbol_for_tab: unknown tab {tab_id}")
            return

        state = self._tab_states[tab_id]
        if not state.symbol:
            return

        # Increment load ID to invalidate any pending jobs for this tab
        state.pending_load_id += 1
        current_load_id = state.pending_load_id

        # CRITICAL: Capture values as local variables to avoid closure issues
        captured_symbol = str(state.symbol)  # Force copy
        captured_tab_id = str(tab_id)  # Force copy
        interval, period = self.datasource.normalize_interval_period(state.interval, state.period)
        captured_interval = str(interval)
        captured_period = str(period)
        state.interval = interval
        state.period = period

        # Use tab's plugin state, or get current global state if none
        plugin_state_snapshot = state.plugin_state.copy() if state.plugin_state else self.plugins.get_state_snapshot()

        self.log.info(f"_reload_symbol_for_tab: tab={captured_tab_id}, symbol={captured_symbol}, interval={captured_interval}, period={captured_period}, load_id={current_load_id}")
        self.statusChanged.emit(tab_id, f"Cargando {captured_symbol} ({captured_interval}/{captured_period})...")

        def job():
            # Log what we're actually fetching inside the job
            self.log.info(f"JOB EXECUTING: tab={captured_tab_id}, symbol={captured_symbol}, load_id={current_load_id}")
            df = self.datasource.fetch_ohlcv(captured_symbol, interval=captured_interval, period=captured_period)
            self.log.info(f"JOB FETCHED: tab={captured_tab_id}, symbol={captured_symbol}, rows={len(df)}, first_close={df['close'].iloc[0] if len(df) > 0 else 'N/A'}, load_id={current_load_id}")
            # Use state_snapshot directly (thread-safe, no global state manipulation)
            df2 = self.plugins.compute_all(df, state_snapshot=plugin_state_snapshot)
            return (df2, current_load_id)

        task = _FetchComputeTask(job, captured_tab_id, plugin_state_snapshot)
        task.signals.done.connect(self._on_loaded)
        task.signals.error.connect(self._on_error)
        self.pool.start(task)

    def _reload_symbol(self):
        """Reload symbol for current tab (legacy, uses _current_tab_id)."""
        if self._current_tab_id:
            self._reload_symbol_for_tab(self._current_tab_id)

    def _on_loaded(self, result):
        """Called when data fetch completes. Result is ((df, load_id), tab_id)."""
        inner_result, tab_id = result

        # Handle both old format (df) and new format ((df, load_id))
        if isinstance(inner_result, tuple) and len(inner_result) == 2:
            df, load_id = inner_result
        else:
            df = inner_result
            load_id = None

        self.log.info(f"_on_loaded: tab_id={tab_id}, rows={len(df)}, load_id={load_id}")

        if tab_id not in self._tab_states:
            self.log.warning(f"Received data for unknown tab: {tab_id}")
            return

        state = self._tab_states[tab_id]

        # Check if this load is still valid (not superseded by a newer load)
        if load_id is not None and load_id != state.pending_load_id:
            self.log.info(f"_on_loaded: IGNORING stale result for tab={tab_id}, load_id={load_id}, current={state.pending_load_id}")
            return

        state.df_main = df

        self.log.info(f"_on_loaded: tab={tab_id}, symbol={state.symbol}, bridge_id={id(state.bridge) if state.bridge else None}")

        # Save current plugin state for this tab if not already saved
        if state.plugin_state is None:
            state.plugin_state = self.plugins.get_state_snapshot()
            self.log.debug(f"Saved initial plugin state for tab: {tab_id}")

        self.statusChanged.emit(tab_id, f"OK: {state.symbol} ({len(df)} velas)")

        # Push data directly to the specific tab (no global state manipulation)
        self._push_all_for_tab(tab_id)

    def _on_error(self, tab_id: str, msg: str):
        self.statusChanged.emit(tab_id, f"Error: {msg}")

    def _recompute_and_push(self):
        state = self._get_current_state()
        if state.df_main is None:
            return
        # recompute from base OHLCV (drop indicator cols)
        base_cols = ["timestamp","open","high","low","close","volume"]
        df_base = state.df_main[base_cols].copy()
        df2 = self.plugins.compute_all(df_base)
        state.df_main = df2
        self._push_indicators_only()

    def _to_epoch(self, ts):
        # ts is pandas Timestamp (tz-aware)
        return int(pd.Timestamp(ts).timestamp())

    def _get_series_definitions_with_state(self, plugin_state: dict):
        """
        Collect all series definitions from enabled plugins using explicit state.
        Thread-safe for concurrent calls.
        """
        series_defs = []
        enabled = plugin_state.get("enabled", {})
        configs = plugin_state.get("configs", {})

        for pid, is_enabled in enabled.items():
            if not is_enabled:
                continue
            plugin = self.plugins.get_plugin(pid)
            if not plugin:
                continue

            # Get configuration from state
            cfg = configs.get(pid, {})

            # Get series definitions from plugin (with config for dynamic series)
            defs = plugin.chart_series(cfg)
            if defs:
                series_defs.extend(defs)

        return series_defs

    def _get_series_definitions(self):
        """
        Collect all series definitions from enabled plugins (legacy, uses global state).
        """
        return self._get_series_definitions_with_state(self.plugins.get_state_snapshot())

    def _push_all_for_tab(self, tab_id: str):
        """Push all data to a specific tab (thread-safe, no global state dependency)."""
        self.log.info(f"_push_all_for_tab: START tab_id={tab_id}")

        if tab_id not in self._tab_states:
            self.log.warning(f"_push_all_for_tab: unknown tab {tab_id}")
            return

        state = self._tab_states[tab_id]
        self.log.info(f"_push_all_for_tab: tab={tab_id}, symbol={state.symbol}, bridge_id={id(state.bridge) if state.bridge else None}")

        if state.df_main is None or state.bridge is None:
            self.log.warning(f"_push_all_for_tab: df_main={state.df_main is not None}, bridge={state.bridge is not None}")
            return

        # Wait for bridge to be ready before pushing data
        if not state.bridge.is_ready():
            self.log.debug(f"Bridge not ready yet for {tab_id}, data will be pushed when ready")
            return

        df = state.df_main
        plugin_state = state.plugin_state or self.plugins.get_state_snapshot()

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

        indicators = self._build_indicator_data_with_state(df, plugin_state)
        series_defs = self._get_series_definitions_with_state(plugin_state)

        # Log first and last candle for verification
        if candles:
            self.log.info(f"_push_all_for_tab: tab={tab_id}, symbol={state.symbol}, first_candle={candles[0]}, last_candle={candles[-1]}")

        payload = {
            "type": "all",
            "candles": candles,
            "indicators": indicators,
            "seriesDefs": series_defs
        }
        self.log.info(f"_push_all_for_tab: EMITTING to tab={tab_id}, bridge_id={id(state.bridge)}, {len(candles)} candles")
        state.bridge.push.emit(json.dumps(payload))

    def _push_all(self):
        """Push all data for current tab (legacy, uses _current_tab_id)."""
        if self._current_tab_id:
            self._push_all_for_tab(self._current_tab_id)

    def _push_indicators_only(self):
        state = self._get_current_state()
        if state.df_main is None or state.bridge is None:
            return
        df = state.df_main

        indicators = self._build_indicator_data(df)
        series_defs = self._get_series_definitions()

        payload = {
            "type": "indicators",
            "indicators": indicators,
            "seriesDefs": series_defs
        }
        state.bridge.push.emit(json.dumps(payload))

    def _build_indicator_data_with_state(self, df: pd.DataFrame, plugin_state: dict):
        """
        Build indicator data dict using explicit plugin state.
        Thread-safe for concurrent calls.
        """
        out = {}
        enabled = plugin_state.get("enabled", {})
        configs = plugin_state.get("configs", {})

        # Collect all columns that need to be sent
        columns_needed = set()

        for pid, is_enabled in enabled.items():
            if not is_enabled:
                continue
            plugin = self.plugins.get_plugin(pid)
            if not plugin:
                continue

            cfg = configs.get(pid, {})

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

                # Fibonacci levels (multiple columns in levels array)
                if s.get("type") == "fibonacci_levels":
                    if s.get("columns"):
                        for col in s.get("columns"):
                            columns_needed.add(col)
                    elif s.get("levels"):
                        for level in s.get("levels"):
                            if level.get("column"):
                                columns_needed.add(level.get("column"))

        # Build data for each column
        for col in columns_needed:
            if col in df.columns:
                out[col] = [
                    {"time": self._to_epoch(t), "value": float(v)}
                    for t, v in zip(df["timestamp"], df[col])
                    if pd.notna(v)  # Skip NaN values
                ]

        return out

    def _build_indicator_data(self, df: pd.DataFrame):
        """
        Build indicator data dict (legacy, uses global state).
        """
        return self._build_indicator_data_with_state(df, self.plugins.get_state_snapshot())

    def _save_state_for_tab(self, tab_id: str) -> None:
        """Save chart state for a specific tab's ticker."""
        if tab_id not in self._tab_states:
            return
        state = self._tab_states[tab_id]
        if state.symbol and state.plugin_state:
            # Build indicators state from tab's plugin_state
            indicators_state = {}
            enabled = state.plugin_state.get("enabled", {})
            configs = state.plugin_state.get("configs", {})
            preset_ids = state.plugin_state.get("preset_ids", {})
            for pid in enabled.keys():
                indicators_state[pid] = {
                    "enabled": enabled.get(pid, False),
                    "preset_id": preset_ids.get(pid, ""),
                    "config": configs.get(pid, {})
                }
            # Save to persistent storage
            self.plugins._chart_state[state.symbol] = {
                "interval": state.interval,
                "period": state.period,
                "indicators": indicators_state
            }
            self.plugins._save_chart_state()
            self.log.debug(f"Saved chart state for {state.symbol} from tab {tab_id}")

    def _save_current_state(self) -> None:
        """Save current chart state for the current ticker."""
        if self._current_tab_id:
            # CRITICAL: Always sync plugin_state from global state before saving
            # This ensures any changes made to PluginManager are captured
            state = self._get_current_state()
            state.plugin_state = self.plugins.get_state_snapshot()
            self._save_state_for_tab(self._current_tab_id)

    @Slot(result=str)
    def getChartState(self) -> str:
        """Get saved chart state for current ticker (for QML to sync UI)."""
        state = self._get_current_state()
        if not state.symbol:
            return "{}"
        saved = self.plugins.load_chart_state_for_ticker(state.symbol)
        if saved:
            return json.dumps({
                "interval": saved.get("interval", state.interval),
                "period": saved.get("period", state.period)
            })
        return json.dumps({
            "interval": state.interval,
            "period": state.period
        })

    @Slot(str)
    def cleanupTab(self, tab_id: str):
        """
        Clean up resources when a tab is closed.
        This prevents memory leaks from accumulated tab states.
        """
        if tab_id not in self._tab_states:
            self.log.debug(f"cleanupTab: tab {tab_id} not found in states")
            return

        state = self._tab_states[tab_id]
        self.log.info(f"Cleaning up resources for tab: {tab_id}")

        # Save state for the ticker before cleanup (if there's data)
        if state.symbol:
            self._save_state_for_tab(tab_id)

        # Clear DataFrame reference to free memory
        if state.df_main is not None:
            state.df_main = None

        # Disconnect bridge signals to prevent memory leaks
        if state.bridge is not None:
            try:
                state.bridge.push.disconnect()
            except (RuntimeError, TypeError):
                # Signal might not be connected or already disconnected
                pass
            state.bridge = None

        # Clear plugin state
        state.plugin_state = None

        # Remove from tab states dict
        del self._tab_states[tab_id]
        self.log.info(f"Tab {tab_id} resources cleaned up successfully")
