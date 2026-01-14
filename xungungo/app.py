from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtQml import QQmlApplicationEngine

from xungungo.core.logger import get_logger
from xungungo.data.yfinance_source import YFinanceDataSource
from xungungo.data.yahoo_search import YahooSearchClient
from xungungo.indicators.manager import PluginManager
from xungungo.bridge.chart_bridge import ChartBridge
from xungungo.controllers.ticker_controller import TickerController
from xungungo.controllers.search_controller import SearchController

# Constants for timing configurations
BRIDGE_CONNECTION_DELAY_MS = 100  # Delay before connecting bridge to QML


class App:
    def __init__(self):
        self.log = get_logger("xungungo.app")
        self.engine = QQmlApplicationEngine()

        # Create bridge with engine as parent
        self.bridge = ChartBridge(self.engine)

        # Create components
        self.plugins = PluginManager()
        self.datasource = YFinanceDataSource()
        self.search_client = YahooSearchClient()
        
        # Create controllers
        self.ticker = TickerController(self.datasource, self.plugins, self.bridge)
        self.search = SearchController(self.search_client)

        # Set context properties BEFORE loading QML
        ctx = self.engine.rootContext()
        ctx.setContextProperty("tickerController", self.ticker)
        ctx.setContextProperty("searchController", self.search)

        # Load QML
        qml_path = Path(__file__).resolve().parent / "ui" / "qml" / "Main.qml"
        self.engine.load(QUrl.fromLocalFile(str(qml_path)))
        
        if not self.engine.rootObjects():
            raise RuntimeError("Failed to load QML")

        self.log.info("App initialized successfully")

        # Connect the bridge to the QML proxy after a short delay
        QTimer.singleShot(BRIDGE_CONNECTION_DELAY_MS, self._connect_bridge)
    
    def _connect_bridge(self):
        """
        Connect Python bridge to QML proxy after components are loaded.

        This method searches for the bridgeProxy QML object and establishes
        bidirectional signal connections for communication.
        """
        try:
            root_objects = self.engine.rootObjects()

            if not root_objects:
                self.log.error("No root objects available in QML engine")
                return

            root = root_objects[0]

            # Find the bridgeProxy object by objectName with depth limit
            def find_proxy(obj, depth=0, max_depth=50):
                """Recursively search for bridgeProxy with depth limit."""
                if depth > max_depth:
                    self.log.warning(f"Maximum search depth ({max_depth}) reached")
                    return None

                try:
                    if hasattr(obj, 'objectName') and obj.objectName() == "bridgeProxy":
                        return obj

                    for child in obj.children():
                        result = find_proxy(child, depth + 1, max_depth)
                        if result:
                            return result
                except RuntimeError as e:
                    # QML object might have been deleted
                    self.log.debug(f"Skipping deleted QML object at depth {depth}: {e}")

                return None

            bridge_proxy = find_proxy(root)

            if bridge_proxy:
                self.log.info("Found bridgeProxy, connecting signals...")

                try:
                    # Connect Python bridge push signal to QML proxy push signal
                    self.bridge.push.connect(bridge_proxy.push)

                    # Connect QML proxy readyRequested to Python bridge ready
                    bridge_proxy.readyRequested.connect(self.bridge.ready)

                    self.log.info("Bridge connected successfully!")

                except Exception as conn_err:
                    self.log.error(f"Failed to connect bridge signals: {conn_err}", exc_info=True)

            else:
                self.log.warning("bridgeProxy not found in QML tree")

                # Print object tree for debugging (only at debug level)
                if self.log.level <= 10:  # DEBUG level
                    def print_tree(obj, indent=0, max_indent=10):
                        if indent > max_indent:
                            return
                        try:
                            self.log.debug("  " * indent + f"{obj.__class__.__name__} '{obj.objectName()}'")
                            for child in obj.children():
                                print_tree(child, indent + 1, max_indent)
                        except RuntimeError:
                            pass  # Object was deleted

                    self.log.debug("QML Object Tree:")
                    print_tree(root)

        except IndexError:
            self.log.error("Root object list is empty")
        except Exception as e:
            self.log.error(f"Unexpected error connecting bridge: {e}", exc_info=True)

    def show(self):
        """Show the application window. QML window is shown automatically on load."""
        # QML window shows automatically when loaded, so this is intentionally empty
        pass