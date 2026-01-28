import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property string tabId: ""
    property string selectedSymbol: ""

    Rectangle {
        anchors.fill: parent
        anchors.margins: 12
        color: "#0b0d14"
        border.color: "#2d3345"
        border.width: 1
        radius: 6

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 16

            Text {
                text: "📈"
                font.pixelSize: 48
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                text: root.selectedSymbol
                    ? "Options: " + root.selectedSymbol
                    : "Options Chain"
                color: "#e6e6e6"
                font.pixelSize: 20
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                text: root.selectedSymbol
                    ? "Options data for " + root.selectedSymbol + " coming soon"
                    : "Select a ticker to view options"
                color: "#8b92b0"
                font.pixelSize: 14
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
