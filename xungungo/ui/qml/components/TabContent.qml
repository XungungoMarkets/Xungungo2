import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtWebChannel 1.0

import "../components"
import "../pages"

Rectangle {
    id: root
    color: "#0f111a"

    required property string tabId
    required property int tabIndex
    property string initialSymbol: ""

    property var pluginsModel: []
    property string currentSymbol: ""
    property bool isLoading: false
    property bool initialized: false
    property bool symbolLoaded: false  // Track if symbol data has been loaded

    // Realtime data properties
    property var realtimeData: null
    property bool isRealtimePolling: false
    property string realtimeError: ""

    // Bridge proxy único para este tab
    QtObject {
        id: bridgeProxy
        objectName: "bridgeProxy_" + root.tabId
        WebChannel.id: "chartBridge"  // Use same ID for all tabs (each WebEngineView has isolated context)

        function ready() {
            console.log("QML Bridge ready() called for tab:", root.tabId, "proxy:", objectName)
            readyRequested()
        }

        signal readyRequested()
        signal push(string payload)

        // Debug: log when push signal is received
        onPush: function(payload) {
            var preview = payload.substring(0, 200)
            console.log("QML PUSH RECEIVED - tab:", root.tabId, "proxy:", objectName, "payload_preview:", preview)
        }
    }

    // WebChannel único para este tab
    WebChannel {
        id: webChannel
        registeredObjects: [bridgeProxy]
    }

    // Listen to pluginsChanged signal to update model
    Connections {
        target: tickerController
        function onPluginsChanged(tabId, pluginsJson) {
            // Only process plugins changes for this tab
            if (tabId !== root.tabId) {
                return
            }
            parsePluginsModel(pluginsJson)
        }
    }

    // Listen to status changes (local state only, global status handled by Main.qml)
    Connections {
        target: tickerController
        function onStatusChanged(tabId, msg) {
            // Only process status changes for this tab
            if (tabId !== root.tabId) {
                return
            }
            isLoading = msg.includes("Loading") || msg.includes("Cargando")
        }
    }

    // Listen to realtime controller signals
    Connections {
        target: realtimeController

        function onRealtimeDataReady(tabId, jsonData) {
            // Debug: log all incoming realtime data
            if (appDebug) {
                console.log("onRealtimeDataReady received - incoming tabId:", tabId, "my tabId:", root.tabId)
            }
            if (tabId !== root.tabId) return

            try {
                root.realtimeData = JSON.parse(jsonData)
                root.realtimeError = ""

                // Send realtime price to chart if we have valid data
                if (root.realtimeData && root.realtimeData.lastSalePrice) {
                    var priceStr = root.realtimeData.lastSalePrice.replace("$", "").replace(",", "")
                    var price = parseFloat(priceStr)
                    if (!isNaN(price)) {
                        var timestamp = Math.floor(Date.now() / 1000)
                        var chartUpdate = JSON.stringify({
                            type: "realtime_update",
                            price: price,
                            timestamp: timestamp
                        })
                        bridgeProxy.push(chartUpdate)
                    }
                } else if (appDebug) {
                    console.log("Realtime data received but no lastSalePrice for tab:", root.tabId)
                }
            } catch(e) {
                console.error("Failed to parse realtime data:", e)
            }
        }

        function onRealtimeError(tabId, error) {
            if (tabId !== root.tabId) return
            root.realtimeError = error
        }

        function onPollingChanged(tabId, isPolling) {
            if (tabId !== root.tabId) return
            root.isRealtimePolling = isPolling
        }
    }

    function parsePluginsModel(pluginsJson) {
        try {
            pluginsModel = JSON.parse(pluginsJson)
            if (appDebug) {
                console.log("Plugins model updated for tab", root.tabId, ":", pluginsModel.length, "plugins")
            }
        } catch(e) {
            console.error("Failed to parse plugins for tab", root.tabId, ":", e)
        }
    }

    // Notify controller when this tab becomes visible
    onVisibleChanged: {
        if (visible) {
            tickerController.setCurrentTab(root.tabId)

            // Load symbol data on first view (lazy loading)
            if (root.currentSymbol && !root.symbolLoaded) {
                console.log("Lazy loading symbol for tab:", root.tabId, "symbol:", root.currentSymbol)
                tickerController.loadSymbolForTab(root.tabId, root.currentSymbol)
                root.symbolLoaded = true
            }

            // Start realtime polling if we have a symbol
            if (root.currentSymbol) {
                realtimeController.startPolling(root.tabId, root.currentSymbol)
            }
        } else {
            // Stop polling when tab is hidden
            realtimeController.stopPolling(root.tabId)
        }
    }

    // Handle symbol changes - restart polling for new symbol
    onCurrentSymbolChanged: {
        // Reset realtime data and loaded state when symbol changes
        root.realtimeData = null
        root.realtimeError = ""
        root.symbolLoaded = false

        // Only load if already initialized (avoid double-load during Component.onCompleted)
        // During initialization, Component.onCompleted handles the initial load
        if (root.initialized && root.visible && root.currentSymbol) {
            tickerController.loadSymbolForTab(root.tabId, root.currentSymbol)
            root.symbolLoaded = true
            realtimeController.startPolling(root.tabId, root.currentSymbol)
        }
    }

    // Timer to ensure polling and current tab are set after QML is fully initialized
    // This handles the race condition where the initial tab is already visible
    // but onVisibleChanged doesn't fire because visible was never false
    Timer {
        id: initPollingTimer
        interval: 100
        repeat: false
        onTriggered: {
            if (root.visible && root.currentSymbol) {
                // Ensure this tab is set as current for interval/period changes to work
                tickerController.setCurrentTab(root.tabId)

                if (!root.isRealtimePolling) {
                    console.log("InitPollingTimer: Starting polling for tab:", root.tabId, "symbol:", root.currentSymbol)
                    realtimeController.startPolling(root.tabId, root.currentSymbol)
                }
            }
        }
    }

    Component.onCompleted: {
        console.log("TabContent completed for tab:", root.tabId, "objectName:", bridgeProxy.objectName, "initialSymbol:", root.initialSymbol, "visible:", root.visible)
        tickerController.connectBridge(root.tabId, bridgeProxy)
        parsePluginsModel(tickerController.getPlugins())

        // Store initial symbol but only load if tab is visible (lazy loading)
        if (root.initialSymbol && root.initialSymbol !== "") {
            root.currentSymbol = root.initialSymbol

            // Only load immediately if this tab is already visible
            if (root.visible) {
                // CRITICAL: Set current tab so interval/period changes work correctly
                // onVisibleChanged won't fire for tabs that are already visible on init
                tickerController.setCurrentTab(root.tabId)

                console.log("Tab visible on init, loading symbol:", root.initialSymbol)
                tickerController.loadSymbolForTab(root.tabId, root.initialSymbol)
                root.symbolLoaded = true
                realtimeController.startPolling(root.tabId, root.initialSymbol)
            }
        }

        root.initialized = true

        // Start timer to ensure polling is initiated even if onVisibleChanged didn't fire
        initPollingTimer.start()
    }

    Component.onDestruction: {
        // CRITICAL: Stop polling when tab is destroyed to prevent phantom polling
        console.log("TabContent destroyed for tab:", root.tabId)
        realtimeController.stopPolling(root.tabId)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Separador visual entre tabs principales y submenú
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "#2d3345"
        }

        // Espacio entre tabs principales y submenú
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 8
        }

        // Submenú TabBar
        TabBar {
            id: subMenuBar
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            background: Rectangle {
                color: "transparent"
            }

            TabButton {
                text: "Chart"
                width: implicitWidth
                height: 36
                background: Rectangle {
                    color: subMenuBar.currentIndex === 0 ? "#1a1d2e" : (parent.hovered ? "#15182a" : "transparent")
                    border.color: subMenuBar.currentIndex === 0 ? "#3d4461" : "transparent"
                    border.width: subMenuBar.currentIndex === 0 ? 1 : 0
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    color: subMenuBar.currentIndex === 0 ? "#e6e6e6" : "#8b92b0"
                    font.pixelSize: 13
                    font.bold: subMenuBar.currentIndex === 0
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            TabButton {
                text: "Fundamentals"
                width: implicitWidth
                height: 36
                background: Rectangle {
                    color: subMenuBar.currentIndex === 1 ? "#1a1d2e" : (parent.hovered ? "#15182a" : "transparent")
                    border.color: subMenuBar.currentIndex === 1 ? "#3d4461" : "transparent"
                    border.width: subMenuBar.currentIndex === 1 ? 1 : 0
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    color: subMenuBar.currentIndex === 1 ? "#e6e6e6" : "#8b92b0"
                    font.pixelSize: 13
                    font.bold: subMenuBar.currentIndex === 1
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            TabButton {
                text: "Options"
                width: implicitWidth
                height: 36
                background: Rectangle {
                    color: subMenuBar.currentIndex === 2 ? "#1a1d2e" : (parent.hovered ? "#15182a" : "transparent")
                    border.color: subMenuBar.currentIndex === 2 ? "#3d4461" : "transparent"
                    border.width: subMenuBar.currentIndex === 2 ? 1 : 0
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    color: subMenuBar.currentIndex === 2 ? "#e6e6e6" : "#8b92b0"
                    font.pixelSize: 13
                    font.bold: subMenuBar.currentIndex === 2
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        // Ticker Header with realtime data
        TickerHeader {
            tabId: root.tabId
            symbol: root.currentSymbol
            realtimeData: root.realtimeData
            isPolling: root.isRealtimePolling
            errorMessage: root.realtimeError
        }

        // Contenido del submenú
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: subMenuBar.currentIndex

            // Chart tab
            ChartTab {
                tabId: root.tabId
                webChannel: webChannel
                pluginsModel: root.pluginsModel
                selectedSymbol: root.currentSymbol
            }

            // Fundamentals tab
            AnalysisTab {
                tabId: root.tabId
                selectedSymbol: root.currentSymbol
                isActive: subMenuBar.currentIndex === 1
            }

            // Options tab
            OptionsTab {
                tabId: root.tabId
                selectedSymbol: root.currentSymbol
            }
        }
    }
}
