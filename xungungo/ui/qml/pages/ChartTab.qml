import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtWebEngine 1.10
import QtWebChannel 1.0

import "../components"

Item {
    id: root

    // Properties passed from parent
    property var webChannel
    property var pluginsModel: []

    // State for sidebar visibility
    property bool sidebarVisible: false

    // Track which accordion is expanded
    property string expandedPluginId: ""

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar panel (indicators) - LEFT SIDE
        Rectangle {
            id: sidebar
            Layout.preferredWidth: sidebarVisible ? 350 : 0
            Layout.fillHeight: true
            color: "#1a1d2e"
            clip: true

            Behavior on Layout.preferredWidth {
                NumberAnimation { duration: 200; easing.type: Easing.InOutQuad }
            }

            ScrollView {
                anchors.fill: parent
                anchors.margins: sidebarVisible ? 12 : 0
                clip: true
                visible: sidebarVisible

                ColumnLayout {
                    width: sidebar.width - 24
                    spacing: 8

                    Label {
                        text: "Indicators"
                        font.pixelSize: 18
                        font.bold: true
                        color: "#e6e6e6"
                        Layout.fillWidth: true
                    }

                    Repeater {
                        id: indicatorRepeater
                        model: pluginsModel

                        delegate: IndicatorAccordion {
                            Layout.fillWidth: true
                            pluginData: modelData
                            // Restore expanded state if this was the previously expanded accordion
                            shouldBeExpanded: modelData && modelData.id === root.expandedPluginId

                            // Track expansion changes
                            onExpansionChanged: function(pluginId, isExpanded) {
                                if (isExpanded) {
                                    root.expandedPluginId = pluginId
                                } else if (root.expandedPluginId === pluginId) {
                                    root.expandedPluginId = ""
                                }
                            }
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }
                }
            }
        }

        // Chart area
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // Toggle sidebar button (top-left corner)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                color: "#0b0d14"

                Button {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.margins: 8
                    text: sidebarVisible ? "◀ Hide Indicators" : "▶ Show Indicators"
                    height: 34
                    width: implicitWidth + 20

                    background: Rectangle {
                        color: parent.hovered ? "#2d3345" : "#1a1d2e"
                        border.color: "#3d4461"
                        border.width: 1
                        radius: 4
                    }

                    contentItem: Text {
                        text: parent.text
                        color: "#e6e6e6"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 12
                    }

                    onClicked: sidebarVisible = !sidebarVisible
                }
            }

            // Chart container
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 12
                Layout.topMargin: 0
                color: "#0b0d14"
                border.color: "#2d3345"
                border.width: 1
                radius: 6

                WebEngineView {
                    id: chartView
                    anchors.fill: parent
                    anchors.margins: 2
                    url: Qt.resolvedUrl("../../web/index.html")
                    webChannel: root.webChannel

                    settings.javascriptEnabled: true
                    settings.localContentCanAccessRemoteUrls: true
                    settings.localContentCanAccessFileUrls: true

                    Component.onCompleted: {
                        console.log("ChartTab: WebEngineView created")
                    }

                    onLoadingChanged: function(loadRequest) {
                        if (loadRequest.status === WebEngineView.LoadSucceededStatus) {
                            console.log("ChartTab: WebEngine loaded successfully")
                        } else if (loadRequest.status === WebEngineView.LoadFailedStatus) {
                            console.error("ChartTab: WebEngine failed to load:", loadRequest.errorString)
                        }
                    }

                    onJavaScriptConsoleMessage: function(level, message, lineNumber, sourceId) {
                        console.log("[WEB]", level, message, sourceId + ":" + lineNumber)
                    }
                }
            }
        }
    }
}
