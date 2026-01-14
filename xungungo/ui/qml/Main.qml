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

    // Global status bar API
    function setStatusText(text) {
        globalStatusBar.statusText = text
    }

    function setLoading(loading) {
        // Can be used by pages to show/hide global loading state
        globalStatusBar.statusText = loading ? "Loading..." : "Ready"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Main content area
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: 0

            // Página principal (por ahora solo Ticker)
            TickerPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            // Reservado para futuras páginas
            // AnotherPage { }
        }

        // Global footer status bar
        StatusBar {
            id: globalStatusBar
            appVersion: "v1.0"
        }
    }
}