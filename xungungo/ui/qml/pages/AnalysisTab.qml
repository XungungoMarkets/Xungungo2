import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    Rectangle {
        anchors.fill: parent
        anchors.margins: 12
        color: "#0b0d14"
        border.color: "#2d3345"
        border.width: 1
        radius: 6

        Label {
            anchors.centerIn: parent
            text: "Analysis tab - Coming soon"
            color: "#8b92b0"
            font.pixelSize: 16
        }
    }
}
