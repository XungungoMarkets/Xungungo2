from pathlib import Path

from PySide6 import QtCore
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from xungungo.bridge.chart_bridge import ChartBridge
from xungungo.controllers.ticker_controller import TickerController
from xungungo.data.yfinance_source import YFinanceDataSource
from xungungo.indicators.manager import PluginManager


def run() -> None:
    QtWebEngineQuick.initialize()
    app = QGuiApplication([])
    engine = QQmlApplicationEngine()

    plugin_manager = PluginManager()
    chart_bridge = ChartBridge()
    controller = TickerController(YFinanceDataSource(), plugin_manager, chart_bridge)

    context = engine.rootContext()
    context.setContextProperty("pluginManager", plugin_manager)
    context.setContextProperty("tickerController", controller)
    context.setContextProperty("chartBridge", chart_bridge)

    qml_path = Path(__file__).resolve().parent / "ui" / "qml" / "Main.qml"
    engine.load(QtCore.QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        raise RuntimeError("No se pudo cargar la UI principal.")

    app.exec()
