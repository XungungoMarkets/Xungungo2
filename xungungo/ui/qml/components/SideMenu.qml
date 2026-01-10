import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    color: "#1f2430"
    radius: 0
    border.color: "#2d3345"
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        Label {
            text: "Xungungo"
            color: "white"
            font.pixelSize: 20
        }

        Button {
            text: "Ticker"
            checked: true
            checkable: true
            Layout.fillWidth: true
        }

        Item { Layout.fillHeight: true }
    }
}
