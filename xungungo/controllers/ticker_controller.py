from __future__ import annotations
import json
import pandas as pd
from PySide6.QtCore import QObject, Signal, Slot, QThread, QRunnable, QThreadPool

from xungungo.core.logger import get_logger
from xungungo.data.datasource_base import DataSource
from xungungo.indicators.manager import PluginManager
from xungungo.bridge.chart_bridge import ChartBridge

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

        self.pool = QThreadPool.globalInstance()

    @Slot(result=str)
    def getPlugins(self) -> str:
        return json.dumps(self.plugins.list_plugins())

    @Slot(str, bool)
    def setPluginEnabled(self, plugin_id: str, enabled: bool):
        self.plugins.enable(plugin_id, enabled)
        self.pluginsChanged.emit(self.getPlugins())
        if self.df_main is not None:
            self._recompute_and_push()

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

    @Slot(str)
    def loadSymbol(self, symbol: str):
        symbol = (symbol or "").strip()
        if not symbol:
            return
        self.symbol = symbol
        self.statusChanged.emit(f"Cargando {symbol}...")
        def job():
            df = self.datasource.fetch_ohlcv(symbol)
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

    def _push_all(self):
        if self.df_main is None:
            return
        df = self.df_main
        candles = [
            {
                "time": self._to_epoch(t),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
            }
            for t, o, h, l, c in zip(df["timestamp"], df["open"], df["high"], df["low"], df["close"])
        ]
        payload = {"type": "all", "candles": candles, "indicators": self._build_indicator_series(df)}
        self.bridge.push.emit(json.dumps(payload))

    def _push_indicators_only(self):
        if self.df_main is None:
            return
        df = self.df_main
        payload = {"type": "indicators", "indicators": self._build_indicator_series(df)}
        self.bridge.push.emit(json.dumps(payload))

    def _build_indicator_series(self, df: pd.DataFrame):
        out = {}
        for pid in self.plugins.enabled_plugins():
            plugin = self.plugins.get_plugin(pid)
            if not plugin:
                continue
            for s in plugin.chart_series():
                col = s.get("column")
                sid = s.get("id")
                if col in df.columns:
                    out[sid] = [
                        {"time": self._to_epoch(t), "value": float(v)}
                        for t, v in zip(df["timestamp"], df[col])
                    ]
        return out
