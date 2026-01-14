import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtWebEngine 1.10
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
            console.log("Bridge ready() called via proxy")
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

    // Listen to pluginsChanged signal to update model
    Connections {
        target: tickerController
        function onPluginsChanged(pluginsJson) {
            try {
                pluginsModel = JSON.parse(pluginsJson)
                console.log("Plugins model updated:", pluginsModel.length, "plugins")
            } catch(e) {
                console.error("Failed to parse plugins from signal:", e)
            }
        }
    }

    // Initialize plugins model on component load
    Component.onCompleted: {
        try {
            pluginsModel = JSON.parse(tickerController.getPlugins())
            console.log("Initial plugins loaded:", pluginsModel.length, "plugins")
        } catch(e) {
            console.error("Failed to load initial plugins:", e)
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
                    id: tickerField
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    placeholderText: "BTC-USD, AAPL, SPY..."
                    onSymbolSelected: function(symbol) {
                        tickerController.loadSymbol(symbol)
                    }
                }

                Button {
                    text: "Load"
                    Layout.preferredHeight: 36
                    Layout.preferredWidth: 80
                    onClicked: {
                        console.log("Loading symbol:", tickerField.text)
                        tickerController.loadSymbol(tickerField.text)
                    }
                }

                Label {
                    id: statusLabel
                    text: ""
                    color: "#8b92b0"
                    Layout.preferredWidth: 200
                    elide: Label.ElideRight
                }

                Connections {
                    target: tickerController
                    function onStatusChanged(msg) {
                        console.log("Status changed:", msg)
                        statusLabel.text = msg
                    }
                }
            }
        }

        // Tabs
        TabBar {
            id: tabBar
            Layout.fillWidth: true
            background: Rectangle {
                color: "#1a1d2e"
            }

            TabButton {
                text: "Chart"
            }

            TabButton {
                text: "Analysis"
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
            }

            // Tab 2: Analysis
            AnalysisTab {
            }
        }
    }
}
