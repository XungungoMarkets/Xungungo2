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
