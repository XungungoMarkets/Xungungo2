import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Dialog {
    id: settingsDialog
    title: "Settings"
    modal: true
    anchors.centerIn: parent
    width: 450
    height: 500

    background: Rectangle {
        color: "#1a1d2e"
        border.color: "#3d4461"
        border.width: 1
        radius: 8
    }

    header: Rectangle {
        height: 50
        color: "#0f111a"
        radius: 8

        // Cover bottom corners
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 8
            color: parent.color
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 12

            Text {
                text: "Settings"
                color: "#e6e6e6"
                font.pixelSize: 16
                font.bold: true
            }

            Item { Layout.fillWidth: true }

            // Close button
            Rectangle {
                width: 28
                height: 28
                radius: 4
                color: closeBtn.containsMouse ? "#ef5350" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "\u2715"
                    color: "#e6e6e6"
                    font.pixelSize: 14
                }

                MouseArea {
                    id: closeBtn
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: settingsDialog.close()
                }
            }
        }

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: "#2d3345"
        }
    }

    contentItem: Flickable {
        clip: true
        contentHeight: contentColumn.height
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }

        ColumnLayout {
            id: contentColumn
            width: parent.width
            spacing: 24

            // ─────────────────────────────────────────────────────────────
            // APPEARANCE SECTION
            // ─────────────────────────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: "Appearance"
                    color: "#26a69a"
                    font.pixelSize: 14
                    font.bold: true
                }

                // Theme selector
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text {
                        text: "Theme"
                        color: "#e6e6e6"
                        font.pixelSize: 13
                        Layout.preferredWidth: 120
                    }

                    ComboBox {
                        id: themeCombo
                        Layout.fillWidth: true
                        model: settingsController.availableThemes
                        currentIndex: model.indexOf(settingsController.theme)

                        onActivated: {
                            settingsController.setTheme(model[currentIndex])
                        }

                        background: Rectangle {
                            color: "#0f111a"
                            border.color: themeCombo.hovered ? "#3d4461" : "#2d3345"
                            radius: 4
                        }

                        contentItem: Text {
                            leftPadding: 10
                            text: themeCombo.displayText
                            color: "#e6e6e6"
                            font.pixelSize: 13
                            verticalAlignment: Text.AlignVCenter
                        }

                        popup: Popup {
                            y: themeCombo.height
                            width: themeCombo.width
                            padding: 1

                            background: Rectangle {
                                color: "#1a1d2e"
                                border.color: "#3d4461"
                                radius: 4
                            }

                            contentItem: ListView {
                                clip: true
                                implicitHeight: contentHeight
                                model: themeCombo.popup.visible ? themeCombo.delegateModel : null

                                ScrollBar.vertical: ScrollBar {}
                            }
                        }

                        delegate: ItemDelegate {
                            width: themeCombo.width
                            height: 32

                            background: Rectangle {
                                color: highlighted ? "#3d4461" : "transparent"
                            }

                            contentItem: Text {
                                text: modelData
                                color: "#e6e6e6"
                                font.pixelSize: 13
                                verticalAlignment: Text.AlignVCenter
                            }

                            highlighted: themeCombo.highlightedIndex === index
                        }
                    }
                }

                // Note about light theme
                Text {
                    visible: settingsController.theme === "light"
                    text: "Light theme coming soon"
                    color: "#8b92b0"
                    font.pixelSize: 11
                    font.italic: true
                    Layout.leftMargin: 132
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#2d3345"
            }

            // ─────────────────────────────────────────────────────────────
            // CHART DEFAULTS SECTION
            // ─────────────────────────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: "Chart Defaults"
                    color: "#26a69a"
                    font.pixelSize: 14
                    font.bold: true
                }

                // Default Interval
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text {
                        text: "Default Interval"
                        color: "#e6e6e6"
                        font.pixelSize: 13
                        Layout.preferredWidth: 120
                    }

                    ComboBox {
                        id: intervalCombo
                        Layout.fillWidth: true
                        model: settingsController.availableIntervals
                        currentIndex: model.indexOf(settingsController.defaultInterval)

                        onActivated: {
                            settingsController.setDefaultInterval(model[currentIndex])
                        }

                        background: Rectangle {
                            color: "#0f111a"
                            border.color: intervalCombo.hovered ? "#3d4461" : "#2d3345"
                            radius: 4
                        }

                        contentItem: Text {
                            leftPadding: 10
                            text: intervalCombo.displayText
                            color: "#e6e6e6"
                            font.pixelSize: 13
                            verticalAlignment: Text.AlignVCenter
                        }

                        popup: Popup {
                            y: intervalCombo.height
                            width: intervalCombo.width
                            padding: 1

                            background: Rectangle {
                                color: "#1a1d2e"
                                border.color: "#3d4461"
                                radius: 4
                            }

                            contentItem: ListView {
                                clip: true
                                implicitHeight: Math.min(contentHeight, 200)
                                model: intervalCombo.popup.visible ? intervalCombo.delegateModel : null
                                ScrollBar.vertical: ScrollBar {}
                            }
                        }

                        delegate: ItemDelegate {
                            width: intervalCombo.width
                            height: 32

                            background: Rectangle {
                                color: highlighted ? "#3d4461" : "transparent"
                            }

                            contentItem: Text {
                                text: modelData
                                color: "#e6e6e6"
                                font.pixelSize: 13
                                verticalAlignment: Text.AlignVCenter
                            }

                            highlighted: intervalCombo.highlightedIndex === index
                        }
                    }
                }

                // Default Period
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text {
                        text: "Default Period"
                        color: "#e6e6e6"
                        font.pixelSize: 13
                        Layout.preferredWidth: 120
                    }

                    ComboBox {
                        id: periodCombo
                        Layout.fillWidth: true
                        model: settingsController.availablePeriods
                        currentIndex: model.indexOf(settingsController.defaultPeriod)

                        onActivated: {
                            settingsController.setDefaultPeriod(model[currentIndex])
                        }

                        background: Rectangle {
                            color: "#0f111a"
                            border.color: periodCombo.hovered ? "#3d4461" : "#2d3345"
                            radius: 4
                        }

                        contentItem: Text {
                            leftPadding: 10
                            text: periodCombo.displayText
                            color: "#e6e6e6"
                            font.pixelSize: 13
                            verticalAlignment: Text.AlignVCenter
                        }

                        popup: Popup {
                            y: periodCombo.height
                            width: periodCombo.width
                            padding: 1

                            background: Rectangle {
                                color: "#1a1d2e"
                                border.color: "#3d4461"
                                radius: 4
                            }

                            contentItem: ListView {
                                clip: true
                                implicitHeight: Math.min(contentHeight, 200)
                                model: periodCombo.popup.visible ? periodCombo.delegateModel : null
                                ScrollBar.vertical: ScrollBar {}
                            }
                        }

                        delegate: ItemDelegate {
                            width: periodCombo.width
                            height: 32

                            background: Rectangle {
                                color: highlighted ? "#3d4461" : "transparent"
                            }

                            contentItem: Text {
                                text: modelData
                                color: "#e6e6e6"
                                font.pixelSize: 13
                                verticalAlignment: Text.AlignVCenter
                            }

                            highlighted: periodCombo.highlightedIndex === index
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#2d3345"
            }

            // ─────────────────────────────────────────────────────────────
            // DATA SOURCE SECTION
            // ─────────────────────────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: "Data Source"
                    color: "#26a69a"
                    font.pixelSize: 14
                    font.bold: true
                }

                // Datasource selector
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text {
                        text: "Provider"
                        color: "#e6e6e6"
                        font.pixelSize: 13
                        Layout.preferredWidth: 120
                    }

                    ComboBox {
                        id: datasourceCombo
                        Layout.fillWidth: true
                        model: settingsController.availableDatasources
                        currentIndex: model.indexOf(settingsController.datasource)

                        onActivated: {
                            settingsController.setDatasource(model[currentIndex])
                        }

                        background: Rectangle {
                            color: "#0f111a"
                            border.color: datasourceCombo.hovered ? "#3d4461" : "#2d3345"
                            radius: 4
                        }

                        contentItem: Text {
                            leftPadding: 10
                            text: datasourceCombo.displayText
                            color: "#e6e6e6"
                            font.pixelSize: 13
                            verticalAlignment: Text.AlignVCenter
                        }

                        popup: Popup {
                            y: datasourceCombo.height
                            width: datasourceCombo.width
                            padding: 1

                            background: Rectangle {
                                color: "#1a1d2e"
                                border.color: "#3d4461"
                                radius: 4
                            }

                            contentItem: ListView {
                                clip: true
                                implicitHeight: contentHeight
                                model: datasourceCombo.popup.visible ? datasourceCombo.delegateModel : null
                                ScrollBar.vertical: ScrollBar {}
                            }
                        }

                        delegate: ItemDelegate {
                            width: datasourceCombo.width
                            height: 32

                            background: Rectangle {
                                color: highlighted ? "#3d4461" : "transparent"
                            }

                            contentItem: Text {
                                text: modelData
                                color: "#e6e6e6"
                                font.pixelSize: 13
                                verticalAlignment: Text.AlignVCenter
                            }

                            highlighted: datasourceCombo.highlightedIndex === index
                        }
                    }
                }

                Text {
                    text: "More data providers coming soon (Alpaca, Polygon...)"
                    color: "#8b92b0"
                    font.pixelSize: 11
                    font.italic: true
                    Layout.leftMargin: 132
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#2d3345"
            }

            // ─────────────────────────────────────────────────────────────
            // GENERAL SECTION
            // ─────────────────────────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 12

                Text {
                    text: "General"
                    color: "#26a69a"
                    font.pixelSize: 14
                    font.bold: true
                }

                // Restore tabs on start
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Text {
                        text: "Restore tabs on start"
                        color: "#e6e6e6"
                        font.pixelSize: 13
                        Layout.preferredWidth: 200
                    }

                    Switch {
                        id: restoreTabsSwitch
                        checked: settingsController.restoreTabsOnStart

                        onToggled: {
                            settingsController.setRestoreTabsOnStart(checked)
                        }

                        indicator: Rectangle {
                            implicitWidth: 44
                            implicitHeight: 24
                            x: restoreTabsSwitch.leftPadding
                            y: parent.height / 2 - height / 2
                            radius: 12
                            color: restoreTabsSwitch.checked ? "#26a69a" : "#3d4461"

                            Rectangle {
                                x: restoreTabsSwitch.checked ? parent.width - width - 2 : 2
                                y: 2
                                width: 20
                                height: 20
                                radius: 10
                                color: "#e6e6e6"

                                Behavior on x {
                                    NumberAnimation { duration: 150 }
                                }
                            }
                        }
                    }
                }
            }

            // Spacer
            Item {
                Layout.fillHeight: true
                Layout.minimumHeight: 20
            }

            // Reset button
            RowLayout {
                Layout.fillWidth: true
                Layout.bottomMargin: 10

                Item { Layout.fillWidth: true }

                Button {
                    text: "Reset to Defaults"

                    onClicked: {
                        settingsController.resetToDefaults()
                        // Update UI
                        themeCombo.currentIndex = themeCombo.model.indexOf(settingsController.theme)
                        intervalCombo.currentIndex = intervalCombo.model.indexOf(settingsController.defaultInterval)
                        periodCombo.currentIndex = periodCombo.model.indexOf(settingsController.defaultPeriod)
                        datasourceCombo.currentIndex = datasourceCombo.model.indexOf(settingsController.datasource)
                        restoreTabsSwitch.checked = settingsController.restoreTabsOnStart
                    }

                    background: Rectangle {
                        color: parent.hovered ? "#3d4461" : "#2d3345"
                        radius: 4
                    }

                    contentItem: Text {
                        text: parent.text
                        color: "#e6e6e6"
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }

    // Remove default footer
    footer: Item {}
}
