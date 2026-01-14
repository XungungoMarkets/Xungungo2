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

    // Estructura simple sin sidebar, pero preparada para futuros menús
    StackLayout {
        anchors.fill: parent
        currentIndex: 0
        
        // Página principal (por ahora solo Ticker)
        TickerPage {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        
        // Reservado para futuras páginas
        // AnotherPage { }
    }
}