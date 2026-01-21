import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtWebChannel 1.0

import "../components"

Rectangle {
    id: root
    color: "#0f111a"

    // Proxy object created in QML (can be registered in WebChannel)
    QtObject {
        id: bridgeProxy
        objectName: "bridgeProxy"
        WebChannel.id: "chartBridge"

        function ready() {
            if (appDebug) {
                console.log("Bridge ready() called via proxy")
            }
            readyRequested()
        }

        signal readyRequested()
        signal push(string payload)
    }

    // Create WebChannel and register the PROXY
    WebChannel {
        id: webChannel
        registeredObjects: [bridgeProxy]
    }

    // Plugins model shared with tabs
    property var pluginsModel: []

    function parsePluginsModel(pluginsJson, okLabel, errorLabel) {
        try {
            pluginsModel = JSON.parse(pluginsJson)
            if (appDebug) {
                console.log(okLabel, pluginsModel.length, "plugins")
            }
        } catch(e) {
            console.error(errorLabel, e)
        }
    }

    // Listen to pluginsChanged signal to update model
    Connections {
        target: tickerController
        function onPluginsChanged(pluginsJson) {
            parsePluginsModel(
                pluginsJson,
                "Plugins model updated:",
                "Failed to parse plugins from signal:"
            )
        }
    }

    // Initialize plugins model on component load
    Component.onCompleted: {
        parsePluginsModel(
            tickerController.getPlugins(),
            "Initial plugins loaded:",
            "Failed to load initial plugins:"
        )
    }

    // Loading state
    property bool isLoading: false
    property string currentSymbol: ""

    // Access to main window for global status bar
    function getMainWindow() {
        var item = root
        while (item.parent) {
            item = item.parent
        }
        return item
    }

    Connections {
        target: tickerController
        function onStatusChanged(msg) {
            if (appDebug) {
                console.log("Status changed:", msg)
            }
            // Update global status bar
            var mainWin = getMainWindow()
            if (mainWin && mainWin.setStatusText) {
                mainWin.setStatusText(msg)
            }
            isLoading = msg.includes("Loading") || msg.includes("Cargando")
        }
    }

    // Main content area
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Top search bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: "#1a1d2e"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                AutocompleteField {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    placeholderText: "BTC-USD, AAPL, SPY..."
                    onSymbolSelected: function(symbol) {
                        root.currentSymbol = symbol
                        tickerController.loadSymbol(symbol)
                    }
                }

                // Loader indicator
                BusyIndicator {
                    Layout.preferredHeight: 36
                    Layout.preferredWidth: 36
                    running: isLoading
                    visible: isLoading
                }
            }
        }

        // Tabs
        TabBar {
            id: tabBar
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            spacing: 4

            background: Rectangle {
                color: "#1a1d2e"

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: "#2d3345"
                }
            }

            TabButton {
                text: "Chart"
                height: tabBar.height

                background: Rectangle {
                    color: {
                        if (parent.checked) return "#0f111a"
                        if (parent.hovered) return "#252838"
                        return "transparent"
                    }

                    Rectangle {
                        visible: parent.parent.checked
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        color: "#26a69a"
                    }
                }

                contentItem: Text {
                    text: parent.text
                    color: parent.checked ? "#e6e6e6" : "#8b92b0"
                    font.pixelSize: 13
                    font.bold: parent.checked
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            TabButton {
                text: "Analysis"
                height: tabBar.height

                background: Rectangle {
                    color: {
                        if (parent.checked) return "#0f111a"
                        if (parent.hovered) return "#252838"
                        return "transparent"
                    }

                    Rectangle {
                        visible: parent.parent.checked
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        color: "#26a69a"
                    }
                }

                contentItem: Text {
                    text: parent.text
                    color: parent.checked ? "#e6e6e6" : "#8b92b0"
                    font.pixelSize: 13
                    font.bold: parent.checked
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        // Tab content
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            // Tab 1: Chart
            ChartTab {
                webChannel: webChannel
                pluginsModel: root.pluginsModel
                selectedSymbol: root.currentSymbol
            }

            // Tab 2: Analysis
            AnalysisTab {
            }
        }
    }
}
