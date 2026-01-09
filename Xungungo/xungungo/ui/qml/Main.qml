import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "components"
import "pages"

ApplicationWindow {
    id: root
    width: 1200
    height: 800
    visible: true
    title: "Xungungo"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SideMenu {
            id: sideMenu
            Layout.preferredWidth: 200
            Layout.fillHeight: true
            onTickerSelected: pageLoader.source = Qt.resolvedUrl("pages/TickerPage.qml")
        }

        Loader {
            id: pageLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            source: Qt.resolvedUrl("pages/TickerPage.qml")
        }
    }
}
