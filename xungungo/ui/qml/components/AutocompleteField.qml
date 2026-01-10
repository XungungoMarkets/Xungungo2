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
        y: textField.height
        width: textField.width
        height: Math.min(listView.contentHeight, 300)
        
        padding: 0
        
        background: Rectangle {
            color: "#1a1d2e"
            border.color: "#2d3345"
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
                height: 50
                
                background: Rectangle {
                    color: listView.currentIndex === index ? "#2d3345" : 
                           hovered ? "#252838" : "transparent"
                }
                
                contentItem: ColumnLayout {
                    spacing: 2
                    
                    RowLayout {
                        spacing: 8
                        
                        Label {
                            text: model.symbol
                            font.bold: true
                            font.pixelSize: 13
                            color: "#e6e6e6"
                        }
                        
                        Label {
                            text: model.exch
                            font.pixelSize: 11
                            color: "#888888"
                        }
                        
                        Label {
                            text: model.typeDisp
                            font.pixelSize: 11
                            color: "#666666"
                        }
                    }
                    
                    Label {
                        text: model.longname
                        font.pixelSize: 11
                        color: "#aaaaaa"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
                
                onClicked: {
                    selectSymbol(model.symbol)
                }
            }
            
            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
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