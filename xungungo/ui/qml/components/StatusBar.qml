import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: statusBar

    property alias statusText: statusLabel.text
    property string appVersion: "v1.0"

    Layout.fillWidth: true
    Layout.preferredHeight: 28
    color: "#0d0e15"
    border.color: "#1a1d2e"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 20

        Label {
            id: statusLabel
            text: "Ready"
            color: "#8b92b0"
            font.pixelSize: 12
        }

        Item {
            Layout.fillWidth: true
        }

        Label {
            text: "Xungungo " + statusBar.appVersion
            color: "#4a5168"
            font.pixelSize: 11
        }
    }
}
