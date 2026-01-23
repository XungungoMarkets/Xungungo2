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
        function onPluginsChanged(pluginsJson) {
            parsePluginsModel(pluginsJson)
        }
    }

    // Listen to status changes
    Connections {
        target: tickerController
        function onStatusChanged(tabId, msg) {
            // Only process status changes for this tab
            if (tabId !== root.tabId) {
                return
            }

            if (appDebug) {
                console.log("Status changed for tab", root.tabId, ":", msg)
            }
            var mainWin = getMainWindow()
            if (mainWin && mainWin.setStatusText) {
                mainWin.setStatusText(msg)
            }
            isLoading = msg.includes("Loading") || msg.includes("Cargando")
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

    function getMainWindow() {
        var item = root
        while (item.parent) {
            item = item.parent
        }
        return item
    }

    // Notify controller when this tab becomes visible
    onVisibleChanged: {
        if (visible) {
            tickerController.setCurrentTab(root.tabId)
        }
    }

    Component.onCompleted: {
        console.log("TabContent completed for tab:", root.tabId, "objectName:", bridgeProxy.objectName, "initialSymbol:", root.initialSymbol)
        tickerController.connectBridge(root.tabId, bridgeProxy)
        parsePluginsModel(tickerController.getPlugins())

        // Load initial symbol if exists (use tab-specific loader to avoid race conditions)
        if (root.initialSymbol && root.initialSymbol !== "") {
            root.currentSymbol = root.initialSymbol
            tickerController.loadSymbolForTab(root.tabId, root.initialSymbol)
        }

        root.initialized = true
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Chart area
        ChartTab {
            Layout.fillWidth: true
            Layout.fillHeight: true
            tabId: root.tabId
            webChannel: webChannel
            pluginsModel: root.pluginsModel
            selectedSymbol: root.currentSymbol
        }
    }
}
