import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#1E1E1E"
    signal tickerSelected()

    ColumnLayout {
        anchors.fill: parent
        spacing: 8
        padding: 12

        Label {
            text: "Xungungo"
            color: "#FFFFFF"
            font.pixelSize: 18
            Layout.fillWidth: true
        }

        Button {
            text: "Ticker"
            Layout.fillWidth: true
            onClicked: root.tickerSelected()
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
