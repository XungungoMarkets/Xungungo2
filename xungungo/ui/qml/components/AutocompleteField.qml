import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    
    property alias text: textField.text
    property alias placeholderText: textField.placeholderText
    
    signal symbolSelected(string symbol)
    
    implicitWidth: textField.implicitWidth
    implicitHeight: textField.implicitHeight
    
    TextField {
        id: textField
        anchors.fill: parent
        font.pixelSize: 12
        color: "#e6e6e6"

        background: Rectangle {
            color: "#1a1d2e"
            border.color: textField.activeFocus ? "#3d4461" : "#2d3345"
            border.width: 1
            radius: 4
        }

        onTextChanged: {
            if (text.length > 0) {
                searchController.search(text)
                popup.open()
            } else {
                popup.close()
            }
        }

        onAccepted: {
            if (popup.visible && listView.currentIndex >= 0) {
                var item = resultsModel.get(listView.currentIndex)
                selectSymbol(item.symbol)
            } else {
                root.symbolSelected(text)
            }
        }

        Keys.onDownPressed: {
            if (popup.visible && listView.count > 0) {
                listView.currentIndex = Math.min(listView.currentIndex + 1, listView.count - 1)
                listView.positionViewAtIndex(listView.currentIndex, ListView.Contain)
            }
        }

        Keys.onUpPressed: {
            if (popup.visible && listView.count > 0) {
                listView.currentIndex = Math.max(listView.currentIndex - 1, 0)
                listView.positionViewAtIndex(listView.currentIndex, ListView.Contain)
            }
        }

        Keys.onEscapePressed: {
            popup.close()
        }
    }
    
    Popup {
        id: popup
        y: textField.height + 2
        width: textField.width
        height: Math.min(listView.contentHeight, 300)

        padding: 1

        background: Rectangle {
            color: "#1a1d2e"
            border.color: "#3d4461"
            border.width: 1
            radius: 4
        }
        
        contentItem: ListView {
            id: listView
            clip: true
            currentIndex: -1
            
            model: ListModel {
                id: resultsModel
            }
            
            delegate: ItemDelegate {
                width: listView.width
                height: 54
                highlighted: listView.currentIndex === index

                background: Rectangle {
                    color: highlighted ? "#3d4461" : (hovered ? "#252838" : "transparent")
                    radius: 3
                }

                contentItem: ColumnLayout {
                    spacing: 3
                    anchors.margins: 8

                    RowLayout {
                        spacing: 8

                        Label {
                            text: model.symbol
                            font.bold: true
                            font.pixelSize: 12
                            color: "#e6e6e6"
                        }

                        Label {
                            text: model.exch
                            font.pixelSize: 10
                            color: "#8b92b0"
                        }

                        Label {
                            text: model.typeDisp
                            font.pixelSize: 10
                            color: "#5d6481"
                        }
                    }

                    Label {
                        text: model.longname
                        font.pixelSize: 10
                        color: "#8b92b0"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                onClicked: {
                    selectSymbol(model.symbol)
                }
            }
            
            ScrollBar.vertical: ScrollBar {
                active: true
                policy: ScrollBar.AsNeeded

                background: Rectangle {
                    implicitWidth: 8
                    color: "#1a1d2e"
                    radius: 4
                }

                contentItem: Rectangle {
                    implicitWidth: 6
                    radius: 3
                    color: parent.pressed ? "#5d6481" : "#3d4461"
                }
            }
        }
    }
    
    Connections {
        target: searchController
        function onResultsChanged(jsonResults) {
            resultsModel.clear()
            
            try {
                var results = JSON.parse(jsonResults)
                for (var i = 0; i < results.length; i++) {
                    resultsModel.append(results[i])
                }
                
                if (results.length > 0) {
                    listView.currentIndex = 0
                } else {
                    popup.close()
                }
            } catch (e) {
                console.error("Error parsing search results:", e)
            }
        }
    }
    
    function selectSymbol(symbol) {
        textField.text = symbol
        popup.close()
        root.symbolSelected(symbol)
    }
}