from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtQml import QQmlApplicationEngine

from xungungo.data.yfinance_source import YFinanceDataSource
from xungungo.data.yahoo_search import YahooSearchClient
from xungungo.indicators.manager import PluginManager
from xungungo.bridge.chart_bridge import ChartBridge
from xungungo.controllers.ticker_controller import TickerController
from xungungo.controllers.search_controller import SearchController


class App:
    def __init__(self):
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
        
        print("App initialized successfully")
        
        # Connect the bridge to the QML proxy after a short delay
        QTimer.singleShot(100, self._connect_bridge)
    
    def _connect_bridge(self):
        """Connect Python bridge to QML proxy after components are loaded."""
        try:
            root = self.engine.rootObjects()[0]
            
            # Find the bridgeProxy object by objectName
            def find_proxy(obj):
                if hasattr(obj, 'objectName') and obj.objectName() == "bridgeProxy":
                    return obj
                for child in obj.children():
                    result = find_proxy(child)
                    if result:
                        return result
                return None
            
            bridge_proxy = find_proxy(root)
            
            if bridge_proxy:
                print("Found bridgeProxy, connecting signals...")
                
                # Connect Python bridge push signal to QML proxy push signal
                self.bridge.push.connect(bridge_proxy.push)
                
                # Connect QML proxy readyRequested to Python bridge ready
                bridge_proxy.readyRequested.connect(self.bridge.ready)
                
                print("Bridge connected successfully!")
            else:
                print("WARNING: bridgeProxy not found in QML tree")
                # Print object tree for debugging
                def print_tree(obj, indent=0):
                    print("  " * indent + f"{obj.__class__.__name__} '{obj.objectName()}'")
                    for child in obj.children():
                        print_tree(child, indent + 1)
                print("QML Object Tree:")
                print_tree(root)
        except Exception as e:
            print(f"Error connecting bridge: {e}")
            import traceback
            traceback.print_exc()

    def show(self):
        pass