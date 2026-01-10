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
            // The Python side will connect to this
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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            AutocompleteField {
                id: tickerField
                Layout.preferredWidth: 220
                placeholderText: "BTC-USD, AAPL, SPY..."
                onSymbolSelected: function(symbol) {
                    tickerController.loadSymbol(symbol)
                }
            }

            Button {
                text: "Load"
                onClicked: {
                    console.log("Loading symbol:", tickerField.text)
                    tickerController.loadSymbol(tickerField.text)
                }
            }

            Label {
                id: statusLabel
                text: ""
                color: "white"
                Layout.fillWidth: true
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

        // Indicators
        GroupBox {
            title: "Indicators"
            Layout.fillWidth: true

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 10

                CheckBox {
                    id: kalmanEnabled
                    text: "Kalman"
                    checked: false
                    onToggled: tickerController.setPluginEnabled("kalman", checked)
                }

                Label { text: "fast Q"; visible: kalmanEnabled.checked }
                TextField {
                    id: fastQ
                    text: "0.001"
                    validator: DoubleValidator { bottom: 0.0 }
                    enabled: kalmanEnabled.checked
                    visible: kalmanEnabled.checked
                    Layout.preferredWidth: 100
                }

                Label { text: "slow Q"; visible: kalmanEnabled.checked }
                TextField {
                    id: slowQ
                    text: "0.0001"
                    validator: DoubleValidator { bottom: 0.0 }
                    enabled: kalmanEnabled.checked
                    visible: kalmanEnabled.checked
                    Layout.preferredWidth: 100
                }

                Button {
                    text: "Apply"
                    enabled: kalmanEnabled.checked
                    visible: kalmanEnabled.checked
                    onClicked: tickerController.setKalmanParams("kalman", parseFloat(fastQ.text), parseFloat(slowQ.text))
                }

                Item { Layout.fillWidth: true }
            }
        }

        // Chart
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#0b0d14"
            border.color: "#2d3345"
            border.width: 1
            radius: 6

            WebEngineView {
                id: chartView
                anchors.fill: parent
                anchors.margins: 2
                url: Qt.resolvedUrl("../../web/index.html")
                webChannel: webChannel

                settings.javascriptEnabled: true
                settings.localContentCanAccessRemoteUrls: true
                settings.localContentCanAccessFileUrls: true
                
                Component.onCompleted: {
                    console.log("WebEngineView created")
                }
                
                onLoadingChanged: function(loadRequest) {
                    if (loadRequest.status === WebEngineView.LoadSucceededStatus) {
                        console.log("WebEngine loaded successfully")
                    } else if (loadRequest.status === WebEngineView.LoadFailedStatus) {
                        console.error("WebEngine failed to load:", loadRequest.errorString)
                    }
                }
                
                onJavaScriptConsoleMessage: function(level, message, lineNumber, sourceId) {
                    console.log("[WEB]", level, message, sourceId + ":" + lineNumber)
                }
            }
        }
    }
}