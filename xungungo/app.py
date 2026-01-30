from __future__ import annotations
from pathlib import Path
import os
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine

from xungungo.core.logger import get_logger
from xungungo.data.yfinance_source import YFinanceDataSource
from xungungo.data.yahoo_search import YahooSearchClient
from xungungo.indicators.manager import PluginManager
from xungungo.controllers.ticker_controller import TickerController
from xungungo.controllers.search_controller import SearchController
from xungungo.controllers.tab_manager import TabManager
from xungungo.controllers.analysis_controller import AnalysisController
from xungungo.controllers.realtime_controller import RealtimeController


class App:
    def __init__(self):
        self.log = get_logger("xungungo.app")
        self.engine = QQmlApplicationEngine()

        # Create components
        self.plugins = PluginManager()
        self.datasource = YFinanceDataSource()
        self.search_client = YahooSearchClient()

        # Create TabManager
        self.tab_manager = TabManager()

        # Create controllers (sin bridge inicial, se crean por tab)
        self.ticker = TickerController(self.datasource, self.plugins)
        self.search = SearchController(self.search_client)
        self.analysis = AnalysisController()
        self.realtime = RealtimeController()

        # Connect tab close signal for cleanup (prevents memory leaks)
        self.tab_manager.tabClosed.connect(self.ticker.cleanupTab)
        self.tab_manager.tabClosed.connect(self.realtime.stopPolling)

        # Set context properties BEFORE loading QML
        ctx = self.engine.rootContext()
        ctx.setContextProperty("tickerController", self.ticker)
        ctx.setContextProperty("searchController", self.search)
        ctx.setContextProperty("tabManager", self.tab_manager)
        ctx.setContextProperty("analysisController", self.analysis)
        ctx.setContextProperty("realtimeController", self.realtime)
        ctx.setContextProperty("appDebug", os.getenv("XUNGUNGO_DEBUG") == "1")

        # Load QML
        qml_path = Path(__file__).resolve().parent / "ui" / "qml" / "Main.qml"
        self.engine.load(QUrl.fromLocalFile(str(qml_path)))

        if not self.engine.rootObjects():
            raise RuntimeError("Failed to load QML")

        self.log.info("App initialized successfully")

    def show(self):
        """Show the application window. QML window is shown automatically on load."""
        # QML window shows automatically when loaded, so this is intentionally empty
        pass
