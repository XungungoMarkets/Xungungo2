import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs

Rectangle {
    id: root
    color: "#0b0d14"
    border.color: expanded ? "#3d4461" : "#2d3345"
    border.width: 1
    radius: 6

    property var pluginData: ({})
    property bool expanded: false
    property var pluginConfig: ({})
    property var pendingConfig: ({})  // Temporary config for unapplied changes
    property bool hasUnappliedChanges: false
    property int configVersion: 0  // Increment to force UI refresh
    property var presets: ({})  // Available presets for this plugin
    property string currentPresetId: ""  // Currently selected preset
    property bool shouldBeExpanded: false  // External control for restoring state

    implicitHeight: expanded ? (headerRect.height + configColumn.height + 16) : headerRect.height

    // Signal to notify parent when expansion state changes
    signal expansionChanged(string pluginId, bool isExpanded)

    // Watch for changes in expansion state and notify parent
    onExpandedChanged: {
        if (pluginData && pluginData.id) {
            expansionChanged(pluginData.id, expanded)
        }

        // Load config when expanded
        if (expanded && pluginData.id) {
            loadPluginConfig()
        }
    }

    // Watch for external expansion request
    onShouldBeExpandedChanged: {
        if (shouldBeExpanded !== expanded) {
            expanded = shouldBeExpanded
        }
    }

    function getConfigValue(path, fallback) {
        var parts = path.split(".")
        var cur = pendingConfig  // Use pending config instead of pluginConfig
        for (var i = 0; i < parts.length; i++) {
            if (!cur || cur[parts[i]] === undefined) {
                return fallback
            }
            cur = cur[parts[i]]
        }
        return cur
    }

    function applyPatchLocal(path, value) {
        var parts = path.split(".")
        var cur = pendingConfig  // Use pending config
        for (var i = 0; i < parts.length - 1; i++) {
            if (!cur[parts[i]] || typeof cur[parts[i]] !== "object") {
                cur[parts[i]] = {}
            }
            cur = cur[parts[i]]
        }
        cur[parts[parts.length - 1]] = value
    }

    function setConfigValue(path, value) {
        if (!pluginData || !pluginData.id) {
            return
        }
        if (!path) {
            return
        }
        applyPatchLocal(path, value)
        hasUnappliedChanges = true  // Mark as having unapplied changes

        // Clear current preset ID since config was manually changed
        if (currentPresetId !== "") {
            currentPresetId = ""
        }

    }

    function formatNumber(value, schema) {
        if (value === null || value === undefined) return ""
        if (schema && schema.type === "integer") {
            return String(Math.round(value))
        }
        var num = Number(value)
        if (isNaN(num)) return ""
        return num.toFixed(6)
    }

    function parseNumber(textValue) {
        if (textValue === null || textValue === undefined) return null
        var raw = String(textValue).trim()
        if (!raw.length) return null
        // Remove all spaces and replace comma with period for decimal separator
        raw = raw.replace(/\s/g, "")
        raw = raw.replace(",", ".")
        var num = parseFloat(raw)
        if (isNaN(num)) return null
        return num
    }

    function applyChanges() {
        if (!pluginData || !pluginData.id) return
        if (!hasUnappliedChanges) return

        // Send entire pending config to backend
        tickerController.setPluginConfig(pluginData.id, JSON.stringify(pendingConfig))

        // Update local config to match
        pluginConfig = JSON.parse(JSON.stringify(pendingConfig))
        hasUnappliedChanges = false

    }

    function discardChanges() {
        // Reset pending config to match saved config
        pendingConfig = JSON.parse(JSON.stringify(pluginConfig))
        hasUnappliedChanges = false
        if (pluginData && Object.prototype.hasOwnProperty.call(pluginData, "current_preset_id")) {
            currentPresetId = pluginData.current_preset_id || ""
        }
        configVersion++  // Force UI refresh
    }

    Component {
        id: configFieldComponent

        Item {
            property var fieldSchema: null
            property string fieldPath: ""
            property var fieldValue: null

            width: parent ? parent.width : 0
            implicitHeight: Math.max(fieldLoader.implicitHeight, 24)

            // When fieldValue changes from parent, update the loaded component
            onFieldValueChanged: {
                if (fieldLoader.item && ("fieldValue" in fieldLoader.item)) {
                    fieldLoader.item.fieldValue = fieldValue
                }
            }

            onFieldSchemaChanged: {
                if (fieldLoader.item && ("fieldSchema" in fieldLoader.item)) {
                    fieldLoader.item.fieldSchema = fieldSchema
                }
            }

            onFieldPathChanged: {
                if (fieldLoader.item && ("fieldPath" in fieldLoader.item)) {
                    fieldLoader.item.fieldPath = fieldPath
                }
            }

            Loader {
                id: fieldLoader
                anchors.left: parent.left
                anchors.right: parent.right
                sourceComponent: {
                    if (!fieldSchema) {
                        return null
                    }
                    if (fieldSchema.type === "boolean") return boolFieldComponent
                    if (fieldSchema.enum && fieldSchema.enum.length) return enumFieldComponent
                    if ((fieldSchema.type === "integer" || fieldSchema.type === "number") && fieldSchema.format === "slider") {
                        return sliderFieldComponent
                    }
                    if (fieldSchema.type === "integer" || fieldSchema.type === "number") return numberFieldComponent
                    if (fieldSchema.type === "string") return textFieldComponent
                    if (fieldSchema.type === "array") return arrayFieldComponent
                    return unsupportedFieldComponent
                }
                onLoaded: {
                    if (appDebug) {
                        console.log("Inner field Loader completed for:", fieldPath, "type:", fieldSchema ? fieldSchema.type : "NULL")
                    }
                    if (!item) return
                    if ("fieldSchema" in item) {
                        item.fieldSchema = fieldSchema
                    }
                    if ("fieldPath" in item) {
                        item.fieldPath = fieldPath
                    }
                    if ("fieldValue" in item && fieldValue !== null && fieldValue !== undefined) {
                        item.fieldValue = fieldValue
                    }
                }
            }
        }
    }

    Component {
        id: boolFieldComponent

        Switch {
            property var fieldSchema: null
            property string fieldPath: ""
            property var fieldValue: null
            property bool ready: false

            // Initialize checked from fieldValue
            Component.onCompleted: {
                checked = (fieldValue === true)
                ready = true
            }

            // Update checked when fieldValue changes externally
            onFieldValueChanged: {
                if (ready && fieldValue !== null && fieldValue !== undefined) {
                    var newChecked = (fieldValue === true)
                    if (checked !== newChecked) {
                        checked = newChecked
                    }
                }
            }

            onClicked: {
                if (appDebug) {
                    console.log("  fieldPath:", fieldPath, "(length:", fieldPath ? fieldPath.length : "NULL", ")")
                    console.log("  fieldSchema:", fieldSchema ? "OK" : "NULL")
                }

                if (!ready) {
                    return
                }

                if (!fieldPath || fieldPath === "") {
                    return
                }

                setConfigValue(fieldPath, checked)
            }

            indicator: Rectangle {
                implicitWidth: 40
                implicitHeight: 20
                radius: 10
                color: parent.checked ? "#26a69a" : "#3d4461"
                border.color: parent.checked ? "#26a69a" : "#5d6481"

                Rectangle {
                    x: parent.parent.checked ? parent.width - width - 2 : 2
                    y: 2
                    width: 16
                    height: 16
                    radius: 8
                    color: "#e6e6e6"

                    Behavior on x {
                        NumberAnimation { duration: 100 }
                    }
                }
            }
        }
    }

    Component {
        id: enumFieldComponent

        ComboBox {
            id: enumCombo
            property var fieldSchema: null
            property string fieldPath: ""
            property var fieldValue: null
            property bool ready: false
            implicitHeight: 28
            model: fieldSchema && fieldSchema.enum ? fieldSchema.enum : []
            currentIndex: fieldSchema && fieldSchema.enum ? Math.max(0, fieldSchema.enum.indexOf(fieldValue)) : 0

            onActivated: {
                if (!ready || !fieldSchema || !fieldSchema.enum) return
                setConfigValue(fieldPath, fieldSchema.enum[currentIndex])
            }

            Component.onCompleted: {
                ready = true
            }

            background: Rectangle {
                color: "#1a1d2e"
                border.color: enumCombo.activeFocus ? "#3d4461" : "#2d3345"
                border.width: 1
                radius: 4
            }

            contentItem: Text {
                text: enumCombo.displayText
                font.pixelSize: 11
                color: "#e6e6e6"
                verticalAlignment: Text.AlignVCenter
                leftPadding: 8
                rightPadding: enumCombo.indicator ? (enumCombo.indicator.width + enumCombo.spacing) : 30
            }

            delegate: ItemDelegate {
                width: enumCombo.width
                height: 32
                highlighted: enumCombo.highlightedIndex === index

                background: Rectangle {
                    color: highlighted ? "#3d4461" : "transparent"
                }

                contentItem: Text {
                    text: modelData
                    color: highlighted ? "#ffffff" : "#e6e6e6"
                    font.pixelSize: 11
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 8
                }
            }

            popup: Popup {
                y: enumCombo.height
                width: enumCombo.width
                implicitHeight: Math.min(contentItem.implicitHeight, 300)
                padding: 1

                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: enumCombo.popup.visible ? enumCombo.delegateModel : null
                    currentIndex: enumCombo.highlightedIndex

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

                background: Rectangle {
                    color: "#1a1d2e"
                    border.color: "#3d4461"
                    border.width: 1
                    radius: 4
                }
            }
        }
    }

    Component {
        id: numberFieldComponent

        TextField {
            property var fieldSchema: null
            property string fieldPath: ""
            property var fieldValue: null
            property bool ready: false
            implicitHeight: 28

            text: formatNumber(fieldValue, fieldSchema)
            inputMethodHints: Qt.ImhFormattedNumbersOnly

            // Update text when fieldValue changes externally
            onFieldValueChanged: {
                if (!activeFocus && ready && fieldValue !== undefined && fieldValue !== null) {
                    var newText = formatNumber(fieldValue, fieldSchema)
                    if (text !== newText) {
                        text = newText
                    }
                }
            }

            validator: DoubleValidator {
                bottom: fieldSchema && fieldSchema.minimum !== undefined ? fieldSchema.minimum : -1e12
                notation: DoubleValidator.StandardNotation
                locale: "C"  // Use C locale to ensure period as decimal separator
            }

            onEditingFinished: {
                if (!ready) return
                var v = parseNumber(text)
                if (v === null) return
                if (fieldSchema && fieldSchema.type === "integer") {
                    v = Math.round(v)
                }
                if (fieldValue === v) {
                    text = formatNumber(v, fieldSchema)
                    return
                }
                setConfigValue(fieldPath, v)
                text = formatNumber(v, fieldSchema)
            }

            background: Rectangle {
                color: "#1a1d2e"
                border.color: parent.activeFocus ? "#3d4461" : "#2d3345"
                border.width: 1
                radius: 4
            }

            color: "#e6e6e6"
            font.pixelSize: 11
            Component.onCompleted: {
                ready = true
                if (appDebug) {
                    console.log("NumberField loaded:", fieldPath, "=", fieldValue, "schema:", fieldSchema ? "OK" : "NULL")
                }
            }
        }
    }

    Component {
        id: sliderFieldComponent

        RowLayout {
            id: sliderRow
            property var fieldSchema: null
            property string fieldPath: ""
            property var fieldValue: null
            property bool ready: false
            spacing: 8

            // Update slider when fieldValue changes externally
            onFieldValueChanged: {
                if (ready && fieldValue !== undefined && fieldValue !== null) {
                    if (Math.abs(slider.value - fieldValue) > 0.001) {
                        slider.value = fieldValue
                    }
                }
            }

            Component.onCompleted: {
                ready = true
            }

            Slider {
                id: slider
                Layout.fillWidth: true
                implicitHeight: 28

                from: sliderRow.fieldSchema && sliderRow.fieldSchema.minimum !== undefined ? sliderRow.fieldSchema.minimum : 0
                to: sliderRow.fieldSchema && sliderRow.fieldSchema.maximum !== undefined ? sliderRow.fieldSchema.maximum : 100
                stepSize: sliderRow.fieldSchema && sliderRow.fieldSchema.type === "integer" ? 1 : (sliderRow.fieldSchema && sliderRow.fieldSchema.step ? sliderRow.fieldSchema.step : 1)
                value: sliderRow.fieldValue !== null && sliderRow.fieldValue !== undefined ? sliderRow.fieldValue : from

                onMoved: {
                    if (!sliderRow.ready) return
                    var v = sliderRow.fieldSchema && sliderRow.fieldSchema.type === "integer" ? Math.round(value) : value
                    setConfigValue(sliderRow.fieldPath, v)
                }

                background: Rectangle {
                    x: slider.leftPadding
                    y: slider.topPadding + slider.availableHeight / 2 - height / 2
                    implicitWidth: 200
                    implicitHeight: 4
                    width: slider.availableWidth
                    height: implicitHeight
                    radius: 2
                    color: "#2d3345"

                    Rectangle {
                        width: slider.visualPosition * parent.width
                        height: parent.height
                        color: "#26a69a"
                        radius: 2
                    }
                }

                handle: Rectangle {
                    x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                    y: slider.topPadding + slider.availableHeight / 2 - height / 2
                    implicitWidth: 16
                    implicitHeight: 16
                    radius: 8
                    color: slider.pressed ? "#2ea68f" : "#26a69a"
                    border.color: "#1a1d2e"
                    border.width: 2
                }
            }

            Label {
                text: {
                    var v = slider.value
                    if (sliderRow.fieldSchema && sliderRow.fieldSchema.type === "integer") {
                        return String(Math.round(v))
                    }
                    return v.toFixed(2)
                }
                font.pixelSize: 11
                color: "#e6e6e6"
                Layout.preferredWidth: 50
                horizontalAlignment: Text.AlignRight
            }
        }
    }

    Component {
        id: arrayFieldComponent

        TextField {
            id: arrayField
            property var fieldSchema: null
            property string fieldPath: ""
            property var fieldValue: null
            property bool ready: false
            implicitHeight: 28

            // Convert array to comma-separated string for display
            function arrayToString(arr) {
                if (!arr || !Array.isArray(arr)) return ""
                return arr.map(function(v) {
                    if (typeof v === "number") {
                        // Format numbers nicely (remove trailing zeros)
                        return parseFloat(v.toFixed(6)).toString()
                    }
                    return String(v)
                }).join(", ")
            }

            // Convert comma-separated string back to array
            function stringToArray(str, itemType) {
                if (!str || str.trim() === "") return []
                var parts = str.split(",")
                var result = []
                for (var i = 0; i < parts.length; i++) {
                    var trimmed = parts[i].trim()
                    if (trimmed === "") continue

                    if (itemType === "number" || itemType === "integer") {
                        var num = parseFloat(trimmed)
                        if (!isNaN(num)) {
                            result.push(itemType === "integer" ? Math.round(num) : num)
                        }
                    } else if (itemType === "boolean") {
                        result.push(trimmed.toLowerCase() === "true")
                    } else {
                        result.push(trimmed)
                    }
                }
                return result
            }

            text: arrayToString(fieldValue)

            onFieldValueChanged: {
                if (!activeFocus && ready && fieldValue !== undefined && fieldValue !== null) {
                    var newText = arrayToString(fieldValue)
                    if (text !== newText) {
                        text = newText
                    }
                }
            }

            onEditingFinished: {
                if (!ready || !fieldSchema) return
                var itemType = (fieldSchema.items && fieldSchema.items.type) ? fieldSchema.items.type : "string"
                var arr = stringToArray(text, itemType)
                setConfigValue(fieldPath, arr)
                // Reformat the display
                text = arrayToString(arr)
            }

            placeholderText: "Enter values separated by commas"

            background: Rectangle {
                color: "#1a1d2e"
                border.color: parent.activeFocus ? "#3d4461" : "#2d3345"
                border.width: 1
                radius: 4
            }

            color: "#e6e6e6"
            font.pixelSize: 11
            Component.onCompleted: {
                ready = true
            }
        }
    }

    Component {
        id: textFieldComponent

        TextField {
            property var fieldSchema: null
            property string fieldPath: ""
            property var fieldValue: null
            property bool ready: false
            implicitHeight: 28

            text: fieldValue !== undefined && fieldValue !== null ? String(fieldValue) : ""

            onFieldValueChanged: {
                if (!activeFocus && ready && fieldValue !== undefined && fieldValue !== null) {
                    var newText = String(fieldValue)
                    if (text !== newText) {
                        text = newText
                    }
                }
            }

            onEditingFinished: {
                if (!ready) return
                setConfigValue(fieldPath, text)
            }

            background: Rectangle {
                color: "#1a1d2e"
                border.color: parent.activeFocus ? "#3d4461" : "#2d3345"
                border.width: 1
                radius: 4
            }

            color: "#e6e6e6"
            font.pixelSize: 11
            Component.onCompleted: {
                ready = true
            }
        }
    }

    Component {
        id: unsupportedFieldComponent

        Label {
            property var fieldSchema: null
            property string fieldPath: ""
            property var fieldValue: null
            text: "Unsupported field type"
            font.pixelSize: 11
            color: "#5d6481"
        }
    }

    Component {
        id: configSectionComponent

        ColumnLayout {
            property var schema
            property string pathPrefix: ""
            Layout.fillWidth: true
            spacing: 8

            Repeater {
                model: (schema && schema.properties) ? Object.keys(schema.properties) : []

                delegate: ColumnLayout {
                    property var fieldSchema: schema.properties[modelData]
                    property string fieldKey: modelData
                    property string fieldPath: pathPrefix ? (pathPrefix + "." + fieldKey) : fieldKey
                    Layout.fillWidth: true
                    spacing: 6

                    ColumnLayout {
                        property var fieldSchemaLocal: fieldSchema
                        property string fieldKeyLocal: fieldKey
                        property string fieldPathLocal: fieldPath

                        Layout.fillWidth: true
                        spacing: 6
                        visible: fieldSchemaLocal && fieldSchemaLocal.type === "object"

                        Label {
                            text: parent.fieldSchemaLocal.title || parent.fieldKeyLocal
                            font.pixelSize: 12
                            font.bold: true
                            color: "#e6e6e6"
                            Layout.fillWidth: true
                        }

                        Loader {
                            Layout.fillWidth: true
                            sourceComponent: configSectionComponent
                            onLoaded: {
                                if (item) {
                                    item.schema = parent.fieldSchemaLocal
                                    item.pathPrefix = parent.fieldPathLocal
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        property var fieldSchemaLocal: fieldSchema
                        property string fieldKeyLocal: fieldKey
                        property string fieldPathLocal: fieldPath

                        Layout.fillWidth: true
                        spacing: 6
                        visible: fieldSchemaLocal && fieldSchemaLocal.type !== "object"

                        Label {
                            text: parent.fieldSchemaLocal && parent.fieldSchemaLocal.title ? parent.fieldSchemaLocal.title : parent.fieldKeyLocal
                            font.pixelSize: 11
                            color: "#8b92b0"
                        }

                        Loader {
                            id: fieldComponentLoader
                            Layout.fillWidth: true

                            property var myFieldSchema: parent.fieldSchemaLocal
                            property string myFieldPath: parent.fieldPathLocal
                            property int myVersion: configVersion

                            sourceComponent: configFieldComponent

                            onLoaded: {
                                if (item) {
                                    if (appDebug) {
                                        console.log("  Setting fieldSchema:", myFieldSchema ? "OK" : "NULL")
                                    }
                                    item.fieldPath = myFieldPath
                                    item.fieldSchema = myFieldSchema

                                    // Trigger initial value load
                                    if (myFieldSchema && myFieldPath) {
                                        var initialValue = getConfigValue(myFieldPath, myFieldSchema.default)
                                        item.fieldValue = initialValue
                                    }
                                }
                            }

                            // Watch for config version changes
                            onMyVersionChanged: {
                                if (item && myFieldSchema && myFieldPath) {
                                    var newValue = getConfigValue(myFieldPath, myFieldSchema.default)
                                    item.fieldValue = newValue
                                }
                            }

                            onMyFieldPathChanged: {
                                if (item && myFieldPath) {
                                    item.fieldPath = myFieldPath
                                    if (myFieldSchema) {
                                        var refreshedValue = getConfigValue(myFieldPath, myFieldSchema.default)
                                        item.fieldValue = refreshedValue
                                    }
                                }
                            }
                        }

                        Label {
                            text: parent.fieldSchemaLocal && parent.fieldSchemaLocal.description ? parent.fieldSchemaLocal.description : ""
                            font.pixelSize: 10
                            color: "#5d6481"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            visible: !!(parent.fieldSchemaLocal && parent.fieldSchemaLocal.description)
                        }
                    }
                }
            }
        }
    }

    // Reload config when pluginData changes (e.g., when model updates)
    onPluginDataChanged: {
        if (expanded && pluginData.id) {
            loadPluginConfig()
        }
    }

    function loadPluginConfig() {
        try {
            var cfg = null
            if (pluginData && pluginData.config && Object.keys(pluginData.config).length > 0) {
                cfg = pluginData.config
            } else {
                var configStr = tickerController.getPluginConfig(pluginData.id)
                cfg = JSON.parse(configStr || "{}")
            }

            pluginConfig = cfg
            // Initialize pending config as a deep copy
            pendingConfig = JSON.parse(JSON.stringify(cfg))
            hasUnappliedChanges = false

            // Load presets
            presets = pluginData.presets || {}

            if (pluginData && Object.prototype.hasOwnProperty.call(pluginData, "current_preset_id")) {
                currentPresetId = pluginData.current_preset_id || ""
            } else {
                detectCurrentPreset(cfg)
            }

            configVersion++  // Force UI refresh
        } catch(e) {
            console.error("Failed to load config for", pluginData.id, ":", e)
            pluginConfig = {}
            pendingConfig = {}
            presets = {}
            currentPresetId = ""
            configVersion++
        }
    }

    function detectCurrentPreset(cfg) {
        // Compare current config with all presets to find a match
        if (!presets || !cfg) {
            currentPresetId = ""
            return
        }

        var keys = Object.keys(presets)
        for (var i = 0; i < keys.length; i++) {
            var presetId = keys[i]
            var preset = presets[presetId]
            if (preset.config && configsMatch(cfg, preset.config)) {
                currentPresetId = presetId
                return
            }
        }

        // No match found
        currentPresetId = ""
    }

    function configsMatch(cfg1, cfg2) {
        // Deep comparison of two configs
        return JSON.stringify(cfg1) === JSON.stringify(cfg2)
    }

    function applyPreset(presetId) {
        if (!pluginData || !pluginData.id || !presetId) {
            return
        }

        tickerController.applyPreset(pluginData.id, presetId)
    }

    Behavior on implicitHeight {
        NumberAnimation { duration: 150; easing.type: Easing.InOutQuad }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header (always visible)
        Rectangle {
            id: headerRect
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 10

                // Expand/collapse area (clickeable for expand/collapse)
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    RowLayout {
                        anchors.fill: parent
                        spacing: 10

                        // Expand/collapse indicator
                        Text {
                            text: expanded ? "▼" : "▶"
                            color: "#8b92b0"
                            font.pixelSize: 10
                            Layout.preferredWidth: 12
                        }

                        // Plugin name
                        Label {
                            text: pluginData.name || "Unknown"
                            font.pixelSize: 14
                            font.bold: true
                            color: "#e6e6e6"
                            Layout.fillWidth: true
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: expanded = !expanded
                    }
                }

                // Enable/disable switch (separate from clickeable area)
                Switch {
                    id: enableSwitch
                    checked: pluginData.enabled || false
                    onToggled: {
                        tickerController.setPluginEnabled(pluginData.id, checked)
                    }

                    indicator: Rectangle {
                        implicitWidth: 40
                        implicitHeight: 20
                        radius: 10
                        color: enableSwitch.checked ? "#26a69a" : "#3d4461"
                        border.color: enableSwitch.checked ? "#26a69a" : "#5d6481"

                        Rectangle {
                            x: enableSwitch.checked ? parent.width - width - 2 : 2
                            y: 2
                            width: 16
                            height: 16
                            radius: 8
                            color: "#e6e6e6"

                            Behavior on x {
                                NumberAnimation { duration: 100 }
                            }
                        }
                    }
                }
            }
        }

        // Configuration panel (collapsible)
        ColumnLayout {
            id: configColumn
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            Layout.bottomMargin: 12
            spacing: 8
            visible: expanded
            opacity: expanded ? 1.0 : 0.0

            Behavior on opacity {
                NumberAnimation { duration: 150 }
            }

            // Description
            Label {
                text: pluginData.description || "No description available"
                font.pixelSize: 11
                color: "#8b92b0"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: "#2d3345"
            }

            // Presets Selector
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                visible: presets && Object.keys(presets).length > 0

                Label {
                    text: "Presets"
                    font.pixelSize: 12
                    font.bold: true
                    color: "#e6e6e6"
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    ComboBox {
                        id: presetCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32

                        property var presetModel: {
                            var items = []
                            if (presets) {
                                var keys = Object.keys(presets)
                                for (var i = 0; i < keys.length; i++) {
                                    var preset = presets[keys[i]]
                                    items.push({
                                        id: keys[i],
                                        name: preset.name || keys[i],
                                        description: preset.description || "",
                                        custom: preset.custom || false
                                    })
                                }
                            }
                            return items
                        }

                        model: presetModel
                        textRole: "name"
                        valueRole: "id"

                        currentIndex: -1

                        property string placeholderText: "Select a preset..."

                        function presetIndexForId(presetId) {
                            if (!presetModel || presetModel.length === 0) {
                                return -1
                            }
                            for (var i = 0; i < presetModel.length; i++) {
                                if (presetModel[i].id === presetId) {
                                    return i
                                }
                            }
                            return -1
                        }

                        function updateDisplayText() {
                            if (currentIndex >= 0 && presetModel && presetModel[currentIndex]) {
                                displayText = presetModel[currentIndex].name || presetModel[currentIndex].id
                            } else {
                                displayText = placeholderText
                            }
                        }

                        function syncSelection() {
                            if (!root.currentPresetId || !presetModel || presetModel.length === 0) {
                                if (currentIndex !== -1) {
                                    currentIndex = -1
                                }
                                updateDisplayText()
                                return
                            }
                            var idx = presetIndexForId(root.currentPresetId)
                            if (currentIndex !== idx) {
                                currentIndex = idx
                            }
                            updateDisplayText()
                        }

                        Component.onCompleted: Qt.callLater(syncSelection)
                        onModelChanged: Qt.callLater(syncSelection)
                        onCurrentIndexChanged: updateDisplayText()

                        Connections {
                            target: root
                            function onCurrentPresetIdChanged() {
                                Qt.callLater(presetCombo.syncSelection)
                            }
                        }

                        delegate: ItemDelegate {
                            width: presetCombo.popup.width
                            height: contentColumn.height + 16
                            highlighted: presetCombo.highlightedIndex === index

                            contentItem: Item {
                                anchors.fill: parent

                                ColumnLayout {
                                    id: contentColumn
                                    anchors.left: parent.left
                                    anchors.right: deleteBtn.visible ? deleteBtn.left : parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: 2

                                    RowLayout {
                                        spacing: 6

                                        Label {
                                            text: modelData.name
                                            font.pixelSize: 11
                                            color: highlighted ? "#ffffff" : "#e6e6e6"
                                            font.bold: modelData.custom
                                        }

                                        Label {
                                            text: "(Custom)"
                                            font.pixelSize: 9
                                            color: highlighted ? "#cccccc" : "#8b92b0"
                                            visible: modelData.custom
                                        }
                                    }

                                    Label {
                                        text: modelData.description
                                        font.pixelSize: 9
                                        color: highlighted ? "#cccccc" : "#8b92b0"
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                        visible: modelData.description !== ""
                                    }
                                }

                                // Delete button for custom presets
                                Button {
                                    id: deleteBtn
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.rightMargin: 8
                                    width: 24
                                    height: 24
                                    visible: modelData.custom

                                    text: "×"

                                    background: Rectangle {
                                        color: parent.hovered ? "#ef5350" : "transparent"
                                        border.color: parent.hovered ? "#ef5350" : "#5d6481"
                                        border.width: 1
                                        radius: 3
                                    }

                                    contentItem: Text {
                                        text: parent.text
                                        color: parent.hovered ? "#ffffff" : "#8b92b0"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: 16
                                        font.bold: true
                                    }

                                    onClicked: {
                                        var presetId = modelData.id
                                        presetCombo.popup.close()
                                        var success = tickerController.deleteCustomPreset(pluginData.id, presetId)
                                        if (success) {
                                            loadPluginConfig()
                                        } else {
                                            console.error("  Failed to delete preset")
                                        }
                                    }
                                }
                            }

                            background: Rectangle {
                                color: highlighted ? "#3d4461" : "transparent"
                            }
                        }

                        popup: Popup {
                            y: presetCombo.height
                            width: presetCombo.width
                            implicitHeight: Math.min(contentItem.implicitHeight, 300)
                            padding: 1

                            contentItem: ListView {
                                clip: true
                                implicitHeight: contentHeight
                                model: presetCombo.popup.visible ? presetCombo.delegateModel : null
                                currentIndex: presetCombo.highlightedIndex

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

                            background: Rectangle {
                                color: "#1a1d2e"
                                border.color: "#3d4461"
                                border.width: 1
                                radius: 4
                            }
                        }

                        background: Rectangle {
                            color: "#1a1d2e"
                            border.color: presetCombo.activeFocus ? "#3d4461" : "#2d3345"
                            border.width: 1
                            radius: 4
                        }

                        contentItem: Text {
                            text: presetCombo.displayText
                            font.pixelSize: 11
                            color: "#e6e6e6"
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 8
                            rightPadding: presetCombo.indicator ? (presetCombo.indicator.width + presetCombo.spacing) : 30
                        }

                        onActivated: function(index) {
                            if (model && model[index]) {
                                applyPreset(model[index].id)
                            }
                        }
                    }

                    Button {
                        text: "Save as..."
                        Layout.preferredHeight: 32
                        Layout.preferredWidth: 80
                        visible: hasUnappliedChanges

                        background: Rectangle {
                            color: parent.hovered ? "#3d4461" : "#2d3345"
                            border.color: "#5d6481"
                            border.width: 1
                            radius: 4
                        }

                        contentItem: Text {
                            text: parent.text
                            color: "#8b92b0"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 10
                        }

                        onClicked: {
                            saveAsPresetDialog.open()
                        }
                    }
                }

                Label {
                    text: "Select a preset to quickly configure this indicator"
                    font.pixelSize: 10
                    color: "#5d6481"
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: "#2d3345"
                visible: presets && Object.keys(presets).length > 0
            }

            // Configuration fields placeholder
            Label {
                text: "Configuration"
                font.pixelSize: 12
                font.bold: true
                color: "#e6e6e6"
                Layout.fillWidth: true
            }

            Loader {
                id: configLoader
                Layout.fillWidth: true
                sourceComponent: configSectionComponent
                visible: pluginData.schema && pluginData.schema.properties && Object.keys(pluginData.schema.properties).length > 0
                onLoaded: {
                    if (item) {
                        item.schema = pluginData.schema
                        item.pathPrefix = ""
                    }
                }
            }

            Label {
                text: "No configuration options available"
                font.pixelSize: 11
                color: "#5d6481"
                visible: !configLoader.visible
                Layout.fillWidth: true
            }

            // Apply/Discard buttons
            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 8
                spacing: 8
                visible: hasUnappliedChanges

                Item { Layout.fillWidth: true }  // Spacer

                Button {
                    text: "Discard"
                    Layout.preferredHeight: 28
                    Layout.preferredWidth: 80

                    background: Rectangle {
                        color: parent.hovered ? "#3d4461" : "#2d3345"
                        border.color: "#5d6481"
                        border.width: 1
                        radius: 4
                    }

                    contentItem: Text {
                        text: parent.text
                        color: "#8b92b0"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 11
                    }

                    onClicked: discardChanges()
                }

                Button {
                    text: "Apply"
                    Layout.preferredHeight: 28
                    Layout.preferredWidth: 80

                    background: Rectangle {
                        color: parent.hovered ? "#2ea68f" : "#26a69a"
                        border.color: "#26a69a"
                        border.width: 1
                        radius: 4
                    }

                    contentItem: Text {
                        text: parent.text
                        color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 11
                        font.bold: true
                    }

                    onClicked: applyChanges()
                }
            }
        }
    }

    // Dialog for saving custom presets
    Dialog {
        id: saveAsPresetDialog
        title: "Save Custom Preset"
        modal: true
        anchors.centerIn: parent
        width: 400

        background: Rectangle {
            color: "#1a1d2e"
            border.color: "#3d4461"
            border.width: 1
            radius: 6
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 12

            Label {
                text: "Create a new preset from current configuration"
                font.pixelSize: 11
                color: "#8b92b0"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Label {
                    text: "Preset ID (unique identifier):"
                    font.pixelSize: 11
                    color: "#e6e6e6"
                }

                TextField {
                    id: presetIdField
                    Layout.fillWidth: true
                    placeholderText: "e.g., my_custom_settings"
                    color: "#e6e6e6"
                    font.pixelSize: 11

                    background: Rectangle {
                        color: "#0b0d14"
                        border.color: parent.activeFocus ? "#3d4461" : "#2d3345"
                        border.width: 1
                        radius: 4
                    }

                    validator: RegularExpressionValidator {
                        regularExpression: /^[a-z0-9_]+$/
                    }
                }

                Label {
                    text: "Use lowercase letters, numbers, and underscores only"
                    font.pixelSize: 9
                    color: "#5d6481"
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Label {
                    text: "Display Name:"
                    font.pixelSize: 11
                    color: "#e6e6e6"
                }

                TextField {
                    id: presetNameField
                    Layout.fillWidth: true
                    placeholderText: "e.g., My Custom Settings"
                    color: "#e6e6e6"
                    font.pixelSize: 11

                    background: Rectangle {
                        color: "#0b0d14"
                        border.color: parent.activeFocus ? "#3d4461" : "#2d3345"
                        border.width: 1
                        radius: 4
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Label {
                    text: "Description:"
                    font.pixelSize: 11
                    color: "#e6e6e6"
                }

                TextArea {
                    id: presetDescField
                    Layout.fillWidth: true
                    Layout.preferredHeight: 60
                    placeholderText: "Brief description of what this preset does..."
                    color: "#e6e6e6"
                    font.pixelSize: 11
                    wrapMode: TextArea.Wrap

                    background: Rectangle {
                        color: "#0b0d14"
                        border.color: parent.activeFocus ? "#3d4461" : "#2d3345"
                        border.width: 1
                        radius: 4
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 8
                spacing: 8

                Item { Layout.fillWidth: true }

                Button {
                    text: "Cancel"
                    Layout.preferredHeight: 32
                    Layout.preferredWidth: 80

                    background: Rectangle {
                        color: parent.hovered ? "#3d4461" : "#2d3345"
                        border.color: "#5d6481"
                        border.width: 1
                        radius: 4
                    }

                    contentItem: Text {
                        text: parent.text
                        color: "#8b92b0"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 11
                    }

                    onClicked: {
                        saveAsPresetDialog.close()
                        presetIdField.text = ""
                        presetNameField.text = ""
                        presetDescField.text = ""
                    }
                }

                Button {
                    text: "Save"
                    Layout.preferredHeight: 32
                    Layout.preferredWidth: 80
                    enabled: presetIdField.text.length > 0 && presetNameField.text.length > 0

                    background: Rectangle {
                        color: parent.enabled ? (parent.hovered ? "#2ea68f" : "#26a69a") : "#2d3345"
                        border.color: parent.enabled ? "#26a69a" : "#5d6481"
                        border.width: 1
                        radius: 4
                    }

                    contentItem: Text {
                        text: parent.text
                        color: parent.enabled ? "#ffffff" : "#5d6481"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 11
                        font.bold: true
                    }

                    onClicked: {
                        var success = tickerController.addCustomPreset(
                            pluginData.id,
                            presetIdField.text,
                            presetNameField.text,
                            presetDescField.text,
                            JSON.stringify(pendingConfig)
                        )

                        if (success) {
                            saveAsPresetDialog.close()
                            presetIdField.text = ""
                            presetNameField.text = ""
                            presetDescField.text = ""
                            // Reload to show new preset
                            loadPluginConfig()
                        } else {
                            console.error("Failed to save custom preset")
                        }
                    }
                }
            }
        }
    }
}
