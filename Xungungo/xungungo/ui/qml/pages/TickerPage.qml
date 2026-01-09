import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtWebEngine 1.9
import QtWebChannel 1.0

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        padding: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: symbolField
                Layout.fillWidth: true
                placeholderText: "BTC-USD, AAPL, SPY..."
                onAccepted: tickerController.loadSymbol(text)
            }

            Button {
                text: "Load"
                onClicked: tickerController.loadSymbol(symbolField.text)
            }
        }

        Label {
            text: tickerController.statusMessage
            color: "#AA0000"
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                color: "#F4F4F4"
                radius: 8
                Layout.preferredWidth: 280
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    Label {
                        text: "Indicadores"
                        font.bold: true
                    }

                    ListView {
                        id: indicatorList
                        Layout.fillWidth: true
                        Layout.preferredHeight: 200
                        model: pluginManager
                        delegate: Item {
                            id: delegateRoot
                            width: indicatorList.width
                            height: 36

                            RowLayout {
                                anchors.fill: parent
                                CheckBox {
                                    checked: enabled
                                    onToggled: tickerController.toggleIndicator(pluginId, checked)
                                }
                                Label {
                                    text: name
                                    Layout.fillWidth: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: tickerController.selectPlugin(pluginId)
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                            }
                        }
                    }

                    Label {
                        text: "Configuración"
                        font.bold: true
                        padding: 4
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Repeater {
                            model: tickerController.selectedSchema
                            delegate: Item {
                                width: parent.width
                                height: 48

                                ColumnLayout {
                                    anchors.fill: parent
                                    Label {
                                        text: modelData.label
                                    }
                                    Loader {
                                        id: inputLoader
                                        Layout.fillWidth: true
                                        sourceComponent: {
                                            if (modelData.type === "select") {
                                                return selectComponent
                                            }
                                            return numberComponent
                                        }
                                    }
                                }

                                Component {
                                    id: numberComponent
                                    TextField {
                                        text: tickerController.selectedConfig[modelData.key] + ""
                                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                                        onEditingFinished: {
                                            var value = parseFloat(text)
                                            if (!isNaN(value)) {
                                                tickerController.updateConfig(tickerController.selectedPluginId, modelData.key, value)
                                            }
                                        }
                                    }
                                }

                                Component {
                                    id: selectComponent
                                    ComboBox {
                                        model: modelData.options
                                        currentIndex: modelData.options.indexOf(tickerController.selectedConfig[modelData.key])
                                        onActivated: tickerController.updateConfig(tickerController.selectedPluginId, modelData.key, currentText)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                color: "#FFFFFF"
                radius: 8
                Layout.fillWidth: true
                Layout.fillHeight: true

                WebEngineView {
                    id: chartView
                    anchors.fill: parent
                    url: Qt.resolvedUrl("../../web/index.html")
                    webChannel: WebChannel {
                        id: webChannel
                        registeredObjects: [chartBridge]
                    }
                }
            }
        }
    }
}
