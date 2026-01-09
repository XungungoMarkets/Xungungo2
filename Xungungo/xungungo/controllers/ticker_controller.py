import json
from typing import Dict, List, Optional

import pandas as pd
from PySide6 import QtCore

from xungungo.bridge.chart_bridge import ChartBridge
from xungungo.core.logger import setup_logger
from xungungo.data.datasource_base import DataSource
from xungungo.indicators.manager import PluginManager


class FetchWorker(QtCore.QObject):
    finished = QtCore.Signal(object, str)

    def __init__(self, datasource: DataSource, symbol: str, interval: str) -> None:
        super().__init__()
        self._datasource = datasource
        self._symbol = symbol
        self._interval = interval

    @QtCore.Slot()
    def run(self) -> None:
        try:
            df = self._datasource.fetch_ohlcv(self._symbol, interval=self._interval)
            if df.empty:
                self.finished.emit(pd.DataFrame(), "No data returned for symbol.")
                return
            self.finished.emit(df, "")
        except Exception as exc:  # noqa: BLE001
            self.finished.emit(pd.DataFrame(), str(exc))


class TickerController(QtCore.QObject):
    statusMessageChanged = QtCore.Signal()
    selectedPluginChanged = QtCore.Signal()
    selectedSchemaChanged = QtCore.Signal()
    selectedConfigChanged = QtCore.Signal()

    def __init__(
        self,
        datasource: DataSource,
        plugin_manager: PluginManager,
        chart_bridge: ChartBridge,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._datasource = datasource
        self._plugin_manager = plugin_manager
        self._chart_bridge = chart_bridge
        self._status_message = ""
        self._df_main = pd.DataFrame()
        self._selected_plugin_id: Optional[str] = None
        self._selected_schema: List[Dict] = []
        self._selected_config: Dict = {}
        self._logger = setup_logger()
        self._chart_ready = False
        self._chart_bridge.ready.connect(self._on_chart_ready)

    @QtCore.Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @QtCore.Property(str, notify=selectedPluginChanged)
    def selectedPluginId(self) -> str:
        return self._selected_plugin_id or ""

    @QtCore.Property("QVariantList", notify=selectedSchemaChanged)
    def selectedSchema(self) -> List[Dict]:
        return self._selected_schema

    @QtCore.Property("QVariantMap", notify=selectedConfigChanged)
    def selectedConfig(self) -> Dict:
        return self._selected_config

    @QtCore.Slot(str)
    def loadSymbol(self, symbol: str) -> None:
        symbol = symbol.strip()
        if not symbol:
            self._set_status("Ingrese un ticker válido.")
            return
        self._set_status("Cargando datos...")
        self._df_main = pd.DataFrame()
        self._chart_bridge.reset.emit()

        self._thread = QtCore.QThread(self)
        worker = FetchWorker(self._datasource, symbol, "1d")
        worker.moveToThread(self._thread)
        self._thread.started.connect(worker.run)
        worker.finished.connect(self._on_fetch_finished)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    @QtCore.Slot(str, bool)
    def toggleIndicator(self, plugin_id: str, enabled: bool) -> None:
        self._plugin_manager.enable(plugin_id, enabled)
        if self._df_main.empty or not self._chart_ready:
            return
        if enabled:
            self._apply_plugin(plugin_id)
        else:
            plugin = self._plugin_manager.get_plugin(plugin_id)
            if not plugin:
                return
            for series in plugin.chart_series():
                self._chart_bridge.setIndicatorVisible.emit(series.series_id, False)

    @QtCore.Slot(str)
    def selectPlugin(self, plugin_id: str) -> None:
        plugin = self._plugin_manager.get_plugin(plugin_id)
        if not plugin:
            return
        self._selected_plugin_id = plugin_id
        self._selected_schema = plugin.config_schema().get("fields", [])
        self._selected_config = self._plugin_manager.config(plugin_id)
        self.selectedPluginChanged.emit()
        self.selectedSchemaChanged.emit()
        self.selectedConfigChanged.emit()

    @QtCore.Slot(str, str, "QVariant")
    def updateConfig(self, plugin_id: str, key: str, value) -> None:
        self._plugin_manager.set_config(plugin_id, {key: value})
        if plugin_id == self._selected_plugin_id:
            self._selected_config = self._plugin_manager.config(plugin_id)
            self.selectedConfigChanged.emit()
        if self._plugin_manager.is_enabled(plugin_id) and not self._df_main.empty:
            self._apply_plugin(plugin_id)

    def df_main(self) -> pd.DataFrame:
        return self._df_main.copy()

    def _on_chart_ready(self) -> None:
        self._chart_ready = True
        if not self._df_main.empty:
            self._refresh_chart()

    def _on_fetch_finished(self, df: pd.DataFrame, error: str) -> None:
        if error:
            self._set_status(f"Error: {error}")
            return
        self._df_main = df
        self._set_status("Datos cargados.")
        if self._chart_ready:
            self._refresh_chart()

    def _refresh_chart(self) -> None:
        candles = self._format_candles(self._df_main)
        self._chart_bridge.setCandles.emit(json.dumps(candles))
        for plugin in self._plugin_manager.list_plugins():
            if self._plugin_manager.is_enabled(plugin.id):
                self._apply_plugin(plugin.id)

    def _apply_plugin(self, plugin_id: str) -> None:
        plugin = self._plugin_manager.get_plugin(plugin_id)
        if not plugin:
            return
        config = self._plugin_manager.config(plugin_id)
        df_enriched = plugin.apply(self._df_main, config)
        for series in plugin.chart_series():
            series_data = self._format_line(df_enriched, series.column)
            self._chart_bridge.setIndicatorSeries.emit(series.series_id, json.dumps(series_data))
            self._chart_bridge.setIndicatorVisible.emit(series.series_id, True)

    def _format_candles(self, df: pd.DataFrame) -> List[Dict]:
        times = (df["timestamp"].astype("int64") // 10**9).tolist()
        return [
            {
                "time": int(t),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
            }
            for t, o, h, l, c in zip(
                times,
                df["open"].tolist(),
                df["high"].tolist(),
                df["low"].tolist(),
                df["close"].tolist(),
            )
        ]

    def _format_line(self, df: pd.DataFrame, column: str) -> List[Dict]:
        times = (df["timestamp"].astype("int64") // 10**9).tolist()
        values = df[column].tolist()
        return [
            {"time": int(t), "value": float(v)}
            for t, v in zip(times, values)
            if pd.notna(v)
        ]

    def _set_status(self, message: str) -> None:
        self._status_message = message
        self.statusMessageChanged.emit()
        self._logger.info(message)
