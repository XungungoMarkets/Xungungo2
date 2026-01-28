import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string tabId: ""
    property string symbol: ""
    property var realtimeData: null
    property bool isPolling: false
    property string errorMessage: ""

    // Computed properties
    readonly property string displayPrice: {
        if (!realtimeData || !realtimeData.lastSalePrice) return "-"
        return realtimeData.lastSalePrice
    }
    readonly property string displayChange: {
        if (!realtimeData || !realtimeData.netChange) return "-"
        return realtimeData.netChange
    }
    readonly property string displayPercent: {
        if (!realtimeData || !realtimeData.percentageChange) return "-"
        return realtimeData.percentageChange
    }
    readonly property string displayTimestamp: {
        if (!realtimeData || !realtimeData.lastTradeTimestamp) return ""
        return realtimeData.lastTradeTimestamp
    }
    readonly property string companyName: {
        if (!realtimeData || !realtimeData.companyName) return symbol
        return realtimeData.companyName
    }
    readonly property string marketStatus: {
        if (!realtimeData || !realtimeData.marketStatus) return ""
        return realtimeData.marketStatus
    }
    readonly property bool isPositive: {
        if (!realtimeData || !realtimeData.deltaIndicator) return true
        return realtimeData.deltaIndicator === "up"
    }

    Layout.fillWidth: true
    Layout.preferredHeight: symbol ? 60 : 0
    color: "#12141f"
    visible: symbol !== ""

    Behavior on Layout.preferredHeight {
        NumberAnimation { duration: 200; easing.type: Easing.InOutQuad }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 24

        // Symbol and company name
        ColumnLayout {
            spacing: 2
            Layout.minimumWidth: 150

            Label {
                text: root.symbol
                color: "#e6e6e6"
                font.pixelSize: 20
                font.bold: true
            }

            Label {
                text: root.companyName !== root.symbol ? root.companyName : ""
                color: "#8b92b0"
                font.pixelSize: 11
                visible: text !== ""
                elide: Text.ElideRight
                Layout.maximumWidth: 200
            }
        }

        // Price
        Label {
            text: root.displayPrice
            color: "#e6e6e6"
            font.pixelSize: 28
            font.bold: true
            Layout.minimumWidth: 100
        }

        // Change indicators
        RowLayout {
            spacing: 8

            // Net change badge
            Rectangle {
                Layout.preferredWidth: changeLabel.width + 16
                Layout.preferredHeight: 26
                radius: 4
                color: root.isPositive ? "#26a69a20" : "#ef535020"

                Label {
                    id: changeLabel
                    anchors.centerIn: parent
                    text: root.displayChange
                    color: root.isPositive ? "#26a69a" : "#ef5350"
                    font.pixelSize: 14
                    font.bold: true
                }
            }

            // Percent change badge
            Rectangle {
                Layout.preferredWidth: percentLabel.width + 16
                Layout.preferredHeight: 26
                radius: 4
                color: root.isPositive ? "#26a69a20" : "#ef535020"

                Label {
                    id: percentLabel
                    anchors.centerIn: parent
                    text: root.displayPercent
                    color: root.isPositive ? "#26a69a" : "#ef5350"
                    font.pixelSize: 14
                    font.bold: true
                }
            }
        }

        Item { Layout.fillWidth: true }

        // Timestamp and status
        ColumnLayout {
            spacing: 4
            Layout.alignment: Qt.AlignRight

            // Market status
            Label {
                text: root.marketStatus
                color: root.marketStatus === "Market Open" ? "#26a69a" : "#8b92b0"
                font.pixelSize: 11
                Layout.alignment: Qt.AlignRight
                visible: text !== ""
            }

            // Last trade timestamp
            Label {
                text: root.displayTimestamp
                color: "#6b7280"
                font.pixelSize: 10
                Layout.alignment: Qt.AlignRight
                visible: text !== ""
            }

            // Polling indicator
            RowLayout {
                spacing: 6
                Layout.alignment: Qt.AlignRight

                Rectangle {
                    id: pollingDot
                    width: 6
                    height: 6
                    radius: 3
                    color: root.isPolling ? "#26a69a" : "#4a5168"

                    SequentialAnimation on opacity {
                        running: root.isPolling
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.3; duration: 500 }
                        NumberAnimation { to: 1.0; duration: 500 }
                    }
                }

                Label {
                    text: root.isPolling ? "Live" : "Paused"
                    color: root.isPolling ? "#26a69a" : "#6b7280"
                    font.pixelSize: 10
                }
            }
        }
    }

    // Bottom border
    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: "#2d3345"
    }

    // Error indicator (shown as tooltip on hover if there's an error)
    ToolTip {
        visible: errorArea.containsMouse && root.errorMessage !== ""
        text: root.errorMessage
        delay: 500
    }

    MouseArea {
        id: errorArea
        anchors.fill: parent
        hoverEnabled: true
        propagateComposedEvents: true
        onClicked: mouse.accepted = false
        onPressed: mouse.accepted = false
        onReleased: mouse.accepted = false
    }
}
