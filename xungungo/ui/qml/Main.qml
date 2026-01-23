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

    // Tabs model - use ListModel to preserve component state
    ListModel {
        id: tabsModel
    }

    function parseTabsModel(tabsJson) {
        try {
            var newTabs = JSON.parse(tabsJson)
            if (appDebug) {
                console.log("Tabs updated:", newTabs.length, "tabs")
            }

            // Update model efficiently to preserve existing delegates
            // 1. Remove tabs that no longer exist
            for (var i = tabsModel.count - 1; i >= 0; i--) {
                var found = false
                for (var j = 0; j < newTabs.length; j++) {
                    if (tabsModel.get(i).id === newTabs[j].id) {
                        found = true
                        break
                    }
                }
                if (!found) {
                    if (appDebug) {
                        console.log("Removing tab:", tabsModel.get(i).id)
                    }
                    tabsModel.remove(i)
                }
            }

            // 2. Add new tabs or update existing ones
            for (var k = 0; k < newTabs.length; k++) {
                var newTab = newTabs[k]
                var existingIndex = -1

                // Find if tab already exists
                for (var m = 0; m < tabsModel.count; m++) {
                    if (tabsModel.get(m).id === newTab.id) {
                        existingIndex = m
                        break
                    }
                }

                if (existingIndex >= 0) {
                    // Update existing tab if title or symbol changed
                    var existing = tabsModel.get(existingIndex)
                    if (existing.title !== newTab.title || existing.symbol !== newTab.symbol) {
                        tabsModel.set(existingIndex, newTab)
                    }
                    // Move to correct position if needed
                    if (existingIndex !== k) {
                        tabsModel.move(existingIndex, k, 1)
                    }
                } else {
                    // Insert new tab at correct position
                    if (appDebug) {
                        console.log("Adding new tab:", newTab.id, "at position", k)
                    }
                    tabsModel.insert(k, newTab)
                }
            }
        } catch(e) {
            console.error("Failed to parse tabs:", e)
        }
    }

    // Global status bar API
    function setStatusText(text) {
        globalStatusBar.statusText = text
    }

    function setLoading(loading) {
        globalStatusBar.statusText = loading ? "Loading..." : "Ready"
    }

    // Initialize tabs
    Component.onCompleted: {
        parseTabsModel(tabManager.getTabs())
    }

    Connections {
        target: tabManager
        function onTabsChanged(tabsJson) {
            parseTabsModel(tabsJson)
        }
    }

    Connections {
        target: tabManager
        function onCurrentTabIndexChanged(index) {
            if (appDebug) {
                console.log("TabManager changed currentIndex to:", index)
            }
            // Don't change if user is interacting with tabs
            if (tabBar.currentIndex !== index) {
                tabBar.currentIndex = index
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Global search bar (nivel superior a los tabs)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: "#1a1d2e"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                AutocompleteField {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    placeholderText: "Search ticker: BTC-USD, AAPL, SPY..."
                    onSymbolSelected: function(symbol) {
                        var newIndex = tabManager.addTabWithSymbol(symbol)
                        tabBar.currentIndex = newIndex
                        tabManager.setCurrentTab(newIndex)
                    }
                }

                Item {
                    Layout.fillWidth: true
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: "#2d3345"
            }
        }

        // Tab bar (nivel superior)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            color: "#1a1d2e"

            RowLayout {
                anchors.fill: parent
                spacing: 0

                // Tabs existentes
                Repeater {
                    model: tabsModel

                    TabButton {
                        id: tabBtn
                        required property int index
                        required property string id
                        required property string title

                        Layout.preferredHeight: 44
                        Layout.minimumWidth: 120
                        Layout.maximumWidth: 200
                        checked: tabBar.currentIndex === index

                        onClicked: {
                            tabBar.currentIndex = index
                            tabManager.setCurrentTab(index)
                        }

                        background: Rectangle {
                            color: {
                                if (parent.checked) return "#0f111a"
                                if (parent.hovered) return "#252838"
                                return "transparent"
                            }

                            Rectangle {
                                visible: parent.parent.checked
                                anchors.bottom: parent.bottom
                                width: parent.width
                                height: 2
                                color: "#26a69a"
                            }
                        }

                        contentItem: RowLayout {
                            spacing: 8
                            anchors.leftMargin: 12
                            anchors.rightMargin: 8

                            Text {
                                Layout.fillWidth: true
                                text: tabBtn.title
                                color: tabBtn.checked ? "#e6e6e6" : "#8b92b0"
                                font.pixelSize: 13
                                font.bold: tabBtn.checked
                                elide: Text.ElideRight
                                horizontalAlignment: Text.AlignLeft
                            }

                            // Close button (solo si hay más de 1 tab)
                            Button {
                                visible: tabsModel.count > 1
                                Layout.preferredWidth: 20
                                Layout.preferredHeight: 20
                                text: "×"

                                onClicked: {
                                    tabManager.closeTab(tabBtn.index)
                                }

                                background: Rectangle {
                                    color: parent.hovered ? "#ef5350" : "transparent"
                                    radius: 3
                                }

                                contentItem: Text {
                                    text: parent.text
                                    color: "#e6e6e6"
                                    font.pixelSize: 16
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                    }
                }

                // Botón "+" para nuevo tab
                Button {
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 44
                    text: "+"

                    onClicked: {
                        var newIndex = tabManager.addTab()
                        tabBar.currentIndex = newIndex
                        tabManager.setCurrentTab(newIndex)
                    }

                    background: Rectangle {
                        color: parent.hovered ? "#252838" : "#1a1d2e"
                    }

                    contentItem: Text {
                        text: parent.text
                        color: "#8b92b0"
                        font.pixelSize: 18
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Item {
                    Layout.fillWidth: true
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: "#2d3345"
            }
        }

        // Content area (StackLayout con TabContent por cada tab)
        StackLayout {
            id: tabBar
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabManager.getCurrentIndex()

            Repeater {
                model: tabsModel

                TabContent {
                    required property int index
                    required property string id
                    required property string title
                    required property string symbol

                    tabId: id
                    tabIndex: index
                    initialSymbol: symbol
                }
            }
        }

        // Global footer status bar
        StatusBar {
            id: globalStatusBar
            appVersion: "v1.0"
        }
    }
}
