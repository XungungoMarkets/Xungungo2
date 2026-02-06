import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: titleBar
    height: 32
    color: "#0f111a"

    // Reference to the main window (must be set by parent)
    required property var targetWindow

    // Signal emitted when settings button is clicked
    signal settingsClicked()

    // Track window state for maximize/restore button
    property bool isMaximized: false

    // Sync isMaximized with actual window state
    Connections {
        target: targetWindow
        function onVisibilityChanged(visibility) {
            titleBar.isMaximized = (visibility === 4)  // Window.Maximized = 4
        }
    }

    // Store window geometry before maximizing
    property real savedX: 0
    property real savedY: 0
    property real savedWidth: 1300
    property real savedHeight: 800

    // Drag area for moving the window with manual Aero Snap simulation
    MouseArea {
        id: dragArea
        anchors.fill: parent
        anchors.rightMargin: windowControls.width

        property point startMousePos: Qt.point(0, 0)
        property point startWindowPos: Qt.point(0, 0)

        onPressed: function(mouse) {
            startMousePos = mapToGlobal(mouse.x, mouse.y)
            startWindowPos = Qt.point(targetWindow.x, targetWindow.y)
            // Save geometry if not maximized
            if (!titleBar.isMaximized) {
                titleBar.savedWidth = targetWindow.width
                titleBar.savedHeight = targetWindow.height
            }
        }

        onPositionChanged: function(mouse) {
            if (pressed) {
                var currentMousePos = mapToGlobal(mouse.x, mouse.y)

                if (titleBar.isMaximized) {
                    // Restore from maximized: position window so cursor stays proportional
                    var relativeX = mouse.x / targetWindow.width
                    titleBar.isMaximized = false
                    targetWindow.showNormal()
                    targetWindow.width = titleBar.savedWidth
                    targetWindow.height = titleBar.savedHeight
                    targetWindow.x = currentMousePos.x - (titleBar.savedWidth * relativeX)
                    targetWindow.y = currentMousePos.y - mouse.y
                    startMousePos = currentMousePos
                    startWindowPos = Qt.point(targetWindow.x, targetWindow.y)
                } else {
                    var deltaX = currentMousePos.x - startMousePos.x
                    var deltaY = currentMousePos.y - startMousePos.y
                    targetWindow.x = startWindowPos.x + deltaX
                    targetWindow.y = startWindowPos.y + deltaY
                }
            }
        }

        onReleased: function(mouse) {
            var globalPos = mapToGlobal(mouse.x, mouse.y)
            // Snap to maximize if released at top edge (y < 5 pixels)
            if (globalPos.y <= 5 && !titleBar.isMaximized) {
                titleBar.savedX = startWindowPos.x
                titleBar.savedY = startWindowPos.y
                targetWindow.showMaximized()
                titleBar.isMaximized = true
            }
        }

        onDoubleClicked: {
            toggleMaximize()
        }
    }

    function toggleMaximize() {
        if (isMaximized) {
            targetWindow.showNormal()
            isMaximized = false
        } else {
            savedX = targetWindow.x
            savedY = targetWindow.y
            savedWidth = targetWindow.width
            savedHeight = targetWindow.height
            targetWindow.showMaximized()
            isMaximized = true
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // App icon/logo area
        Rectangle {
            Layout.preferredWidth: 40
            Layout.fillHeight: true
            color: "transparent"

            Text {
                anchors.centerIn: parent
                text: "X"
                color: "#26a69a"
                font.pixelSize: 16
                font.bold: true
            }
        }

        // Title
        Text {
            Layout.fillWidth: true
            text: targetWindow.title
            color: "#8b92b0"
            font.pixelSize: 12
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        // Window control buttons
        RowLayout {
            id: windowControls
            Layout.fillHeight: true
            spacing: 0

            // Settings button
            Rectangle {
                Layout.preferredWidth: 46
                Layout.fillHeight: true
                color: settingsArea.containsMouse ? "#2d3345" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "\u2699"  // gear icon
                    color: "#e6e6e6"
                    font.pixelSize: 16
                }

                MouseArea {
                    id: settingsArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: titleBar.settingsClicked()
                }
            }

            // Separator
            Rectangle {
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                Layout.topMargin: 6
                Layout.bottomMargin: 6
                color: "#2d3345"
            }

            // Minimize button
            Rectangle {
                Layout.preferredWidth: 46
                Layout.fillHeight: true
                color: minimizeArea.containsMouse ? "#2d3345" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "\u2212"  // minus sign
                    color: "#e6e6e6"
                    font.pixelSize: 16
                }

                MouseArea {
                    id: minimizeArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: targetWindow.showMinimized()
                }
            }

            // Maximize/Restore button
            Rectangle {
                Layout.preferredWidth: 46
                Layout.fillHeight: true
                color: maximizeArea.containsMouse ? "#2d3345" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: titleBar.isMaximized ? "\u2752" : "\u25A1"  // restore or maximize icon
                    color: "#e6e6e6"
                    font.pixelSize: titleBar.isMaximized ? 12 : 14
                }

                MouseArea {
                    id: maximizeArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: titleBar.toggleMaximize()
                }
            }

            // Close button
            Rectangle {
                Layout.preferredWidth: 46
                Layout.fillHeight: true
                color: closeArea.containsMouse ? "#ef5350" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "\u2715"  // X symbol
                    color: "#e6e6e6"
                    font.pixelSize: 14
                }

                MouseArea {
                    id: closeArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: targetWindow.close()
                }
            }
        }
    }

    // Bottom border
    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: "#2d3345"
    }
}
