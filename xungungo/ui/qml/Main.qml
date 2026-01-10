import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "components"
import "pages"

ApplicationWindow {
    id: win
    visible: true
    width: 1300
    height: 800
    title: "Xungungo"

    RowLayout {
        anchors.fill: parent
        SideMenu {
            Layout.preferredWidth: 220
            Layout.fillHeight: true
        }

        TickerPage {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
