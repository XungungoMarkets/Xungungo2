import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: statusBar

    property alias statusText: statusLabel.text
    property string appVersion: "v1.0"
    property bool isLoading: false

    Layout.fillWidth: true
    Layout.preferredHeight: 28
    color: "#0d0e15"
    border.color: "#1a1d2e"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 8

        // Loading indicator
        Item {
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
            visible: statusBar.isLoading

            Rectangle {
                id: loadingDot
                width: 8
                height: 8
                radius: 4
                color: "#26a69a"
                anchors.centerIn: parent

                SequentialAnimation on opacity {
                    running: statusBar.isLoading
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 400 }
                    NumberAnimation { to: 1.0; duration: 400 }
                }
            }
        }

        Label {
            id: statusLabel
            text: "Ready"
            color: statusBar.isLoading ? "#26a69a" : "#8b92b0"
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
