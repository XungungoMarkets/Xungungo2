import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property string tabId: ""
    property string selectedSymbol: ""
    property bool isActive: false
    property bool isLoading: false
    property var analysisData: null
    property string errorMessage: ""

    // Load data when tab becomes active and symbol is set
    onIsActiveChanged: {
        if (isActive && selectedSymbol && !analysisData) {
            loadAnalysis()
        }
    }

    onSelectedSymbolChanged: {
        // Reset data when symbol changes
        analysisData = null
        errorMessage = ""
        if (isActive && selectedSymbol) {
            loadAnalysis()
        }
    }

    function loadAnalysis() {
        if (!selectedSymbol) return
        isLoading = true
        errorMessage = ""
        analysisController.loadAnalysis(selectedSymbol)
    }

    // Connect to analysis controller signals
    Connections {
        target: analysisController

        function onAnalysisReady(symbol, jsonData) {
            if (!symbol || !root.selectedSymbol) return
            if (symbol.toUpperCase() === root.selectedSymbol.toUpperCase()) {
                console.log("AnalysisTab: Received data for", symbol, "length:", jsonData.length)
                try {
                    var parsed = JSON.parse(jsonData)
                    console.log("AnalysisTab: Parsed OK, info keys:", parsed.info ? Object.keys(parsed.info).length : 0)
                    root.analysisData = parsed
                    root.isLoading = false
                    console.log("AnalysisTab: Data assigned successfully")
                } catch(e) {
                    console.log("AnalysisTab: Parse error:", e)
                    root.errorMessage = "Failed to parse analysis data"
                    root.isLoading = false
                }
            }
        }

        function onAnalysisError(symbol, error) {
            if (!symbol || !root.selectedSymbol) return
            if (symbol.toUpperCase() === root.selectedSymbol.toUpperCase()) {
                root.errorMessage = error
                root.isLoading = false
            }
        }

        function onLoadingChanged(symbol, loading) {
            if (!symbol || !root.selectedSymbol) return
            if (symbol.toUpperCase() === root.selectedSymbol.toUpperCase()) {
                root.isLoading = loading
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 12
        color: "#0b0d14"
        border.color: "#2d3345"
        border.width: 1
        radius: 6
        clip: true

        // No symbol selected state
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 16
            visible: !root.selectedSymbol

            Text {
                text: "📊"
                font.pixelSize: 48
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                text: "Stock Fundamentals"
                color: "#e6e6e6"
                font.pixelSize: 20
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                text: "Select a ticker to view fundamental analysis"
                color: "#8b92b0"
                font.pixelSize: 14
                Layout.alignment: Qt.AlignHCenter
            }
        }

        // Loading state
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 16
            visible: root.selectedSymbol && root.isLoading

            BusyIndicator {
                running: root.isLoading
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 48
                Layout.preferredHeight: 48
            }

            Label {
                text: "Loading analysis for " + root.selectedSymbol + "..."
                color: "#8b92b0"
                font.pixelSize: 14
                Layout.alignment: Qt.AlignHCenter
            }
        }

        // Error state
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 16
            visible: root.selectedSymbol && !root.isLoading && root.errorMessage

            Text {
                text: "⚠️"
                font.pixelSize: 48
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                text: "Error loading analysis"
                color: "#ef5350"
                font.pixelSize: 16
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                text: root.errorMessage
                color: "#8b92b0"
                font.pixelSize: 12
                Layout.alignment: Qt.AlignHCenter
                wrapMode: Text.Wrap
                Layout.maximumWidth: 300
            }

            Button {
                text: "Retry"
                Layout.alignment: Qt.AlignHCenter
                onClicked: loadAnalysis()

                background: Rectangle {
                    color: parent.hovered ? "#2d3345" : "#1a1d2e"
                    border.color: "#3d4461"
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    color: "#e6e6e6"
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        // Data loaded state - ScrollView with sections
        ScrollView {
            id: analysisScrollView
            anchors.fill: parent
            anchors.margins: 16
            visible: root.selectedSymbol && !root.isLoading && !root.errorMessage && root.analysisData
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: analysisScrollView.availableWidth
                spacing: 20

                // Header with company name
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Label {
                        text: {
                            if (!root.analysisData || !root.analysisData.info) return root.selectedSymbol
                            return root.analysisData.info.longName || root.analysisData.info.shortName || root.selectedSymbol
                        }
                        color: "#e6e6e6"
                        font.pixelSize: 24
                        font.bold: true
                    }

                    Label {
                        text: {
                            if (!root.analysisData || !root.analysisData.info) return ""
                            var parts = []
                            if (root.analysisData.info.sector) parts.push(root.analysisData.info.sector)
                            if (root.analysisData.info.industry) parts.push(root.analysisData.info.industry)
                            return parts.join(" • ")
                        }
                        color: "#8b92b0"
                        font.pixelSize: 14
                        visible: text !== ""
                    }

                    Label {
                        text: {
                            if (!root.analysisData || !root.analysisData.info) return ""
                            var parts = []
                            if (root.analysisData.info.city) parts.push(root.analysisData.info.city)
                            if (root.analysisData.info.country) parts.push(root.analysisData.info.country)
                            return parts.join(", ")
                        }
                        color: "#6b7280"
                        font.pixelSize: 12
                        visible: text !== ""
                    }
                }

                // Business Summary
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: summaryColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6
                    visible: root.analysisData !== null && root.analysisData.info !== undefined && root.analysisData.info.longBusinessSummary !== undefined && root.analysisData.info.longBusinessSummary !== ""

                    ColumnLayout {
                        id: summaryColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 8

                        Label {
                            text: "About"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        Label {
                            text: {
                                if (!root.analysisData || !root.analysisData.info) return ""
                                return root.analysisData.info.longBusinessSummary || ""
                            }
                            color: "#9ca3af"
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                            maximumLineCount: 6
                            elide: Text.ElideRight
                        }
                    }
                }

                // Key Metrics Grid
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: metricsColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6

                    ColumnLayout {
                        id: metricsColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 12

                        Label {
                            text: "Key Metrics"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 3
                            columnSpacing: 16
                            rowSpacing: 12

                            // Market Cap
                            MetricItem {
                                label: "Market Cap"
                                value: formatLargeNumber(getInfoValue("marketCap"))
                            }

                            // P/E Ratio
                            MetricItem {
                                label: "P/E Ratio"
                                value: formatNumber(getInfoValue("trailingPE"), 2)
                            }

                            // Forward P/E
                            MetricItem {
                                label: "Forward P/E"
                                value: formatNumber(getInfoValue("forwardPE"), 2)
                            }

                            // 52 Week High
                            MetricItem {
                                label: "52W High"
                                value: formatPrice(getInfoValue("fiftyTwoWeekHigh"))
                            }

                            // 52 Week Low
                            MetricItem {
                                label: "52W Low"
                                value: formatPrice(getInfoValue("fiftyTwoWeekLow"))
                            }

                            // Beta
                            MetricItem {
                                label: "Beta"
                                value: formatNumber(getInfoValue("beta"), 2)
                            }

                            // Dividend Yield
                            MetricItem {
                                label: "Dividend Yield"
                                value: formatPercent(getInfoValue("dividendYield"))
                            }

                            // EPS
                            MetricItem {
                                label: "EPS (TTM)"
                                value: formatPrice(getInfoValue("trailingEps"))
                            }

                            // ROE
                            MetricItem {
                                label: "ROE"
                                value: formatPercent(getInfoValue("returnOnEquity"))
                            }

                            // Profit Margin
                            MetricItem {
                                label: "Profit Margin"
                                value: formatPercent(getInfoValue("profitMargins"))
                            }

                            // Revenue
                            MetricItem {
                                label: "Revenue"
                                value: formatLargeNumber(getInfoValue("totalRevenue"))
                            }

                            // Employees
                            MetricItem {
                                label: "Employees"
                                value: {
                                    var emp = getInfoValue("fullTimeEmployees")
                                    return emp ? emp.toLocaleString() : "-"
                                }
                            }
                        }
                    }
                }

                // Price Targets
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: targetsColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6
                    visible: root.analysisData && root.analysisData.info && root.analysisData.info.targetMeanPrice !== undefined

                    ColumnLayout {
                        id: targetsColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 12

                        Label {
                            text: "Analyst Price Targets"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 20

                            MetricItem {
                                label: "Low"
                                value: formatPrice(getInfoValue("targetLowPrice"))
                                valueColor: "#ef5350"
                            }

                            MetricItem {
                                label: "Mean"
                                value: formatPrice(getInfoValue("targetMeanPrice"))
                                valueColor: "#e6e6e6"
                            }

                            MetricItem {
                                label: "High"
                                value: formatPrice(getInfoValue("targetHighPrice"))
                                valueColor: "#26a69a"
                            }

                            MetricItem {
                                label: "Analysts"
                                value: {
                                    var analysts = getInfoValue("numberOfAnalystOpinions")
                                    return analysts !== null ? String(analysts) : "-"
                                }
                            }
                        }
                    }
                }

                // Major Holders
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: holdersColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6
                    visible: root.analysisData && root.analysisData.majorHolders && root.analysisData.majorHolders.length > 0

                    ColumnLayout {
                        id: holdersColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 8

                        Label {
                            text: "Major Holders"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        // Grid layout for Major Holders - 2 columns
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 24
                            rowSpacing: 12

                            Repeater {
                                model: root.analysisData && root.analysisData.majorHolders ? root.analysisData.majorHolders : []

                                RowLayout {
                                    spacing: 12

                                    // Value badge
                                    Rectangle {
                                        Layout.preferredWidth: 70
                                        Layout.preferredHeight: 24
                                        color: modelData && modelData.value && modelData.value.includes("%") ? "#26a69a20" : "#3b82f620"
                                        radius: 4

                                        Label {
                                            anchors.centerIn: parent
                                            text: modelData && modelData.value ? modelData.value : ""
                                            color: modelData && modelData.value && modelData.value.includes("%") ? "#26a69a" : "#3b82f6"
                                            font.pixelSize: 12
                                            font.bold: true
                                        }
                                    }

                                    // Description
                                    Label {
                                        text: modelData && modelData.description ? modelData.description : ""
                                        color: "#9ca3af"
                                        font.pixelSize: 12
                                    }
                                }
                            }
                        }
                    }
                }

                // Institutional Holders
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: instColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6
                    visible: root.analysisData && root.analysisData.institutionalHolders && root.analysisData.institutionalHolders.length > 0

                    ColumnLayout {
                        id: instColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 8

                        Label {
                            text: "Top Institutional Holders"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        Repeater {
                            model: root.analysisData && root.analysisData.institutionalHolders ? root.analysisData.institutionalHolders : []

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16

                                // Percentage badge
                                Rectangle {
                                    Layout.preferredWidth: 55
                                    Layout.preferredHeight: 22
                                    color: "#26a69a20"
                                    radius: 4

                                    Label {
                                        anchors.centerIn: parent
                                        text: {
                                            if (!modelData) return "-"
                                            // Try multiple possible field names for percentage
                                            var pct = modelData["% Out"] ?? modelData["pctHeld"] ?? modelData["% Held"] ?? modelData["pctOut"]
                                            if (pct === undefined || pct === null) return "-"
                                            return (pct * 100).toFixed(2) + "%"
                                        }
                                        color: "#26a69a"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }
                                }

                                // Holder name
                                Label {
                                    text: modelData && modelData.Holder ? modelData.Holder : ""
                                    color: "#e6e6e6"
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                // Shares count
                                Label {
                                    text: {
                                        if (!modelData || !modelData.Shares) return ""
                                        return formatShareCount(modelData.Shares)
                                    }
                                    color: "#6b7280"
                                    font.pixelSize: 11
                                    Layout.preferredWidth: 60
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                        }
                    }
                }

                // Valuation Metrics
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: valuationColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6

                    ColumnLayout {
                        id: valuationColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 12

                        Label {
                            text: "Valuation"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 3
                            columnSpacing: 16
                            rowSpacing: 12

                            MetricItem {
                                label: "PEG Ratio"
                                value: formatNumber(getInfoValue("pegRatio"), 2)
                            }

                            MetricItem {
                                label: "Price/Book"
                                value: formatNumber(getInfoValue("priceToBook"), 2)
                            }

                            MetricItem {
                                label: "Price/Sales"
                                value: formatNumber(getInfoValue("priceToSalesTrailing12Months"), 2)
                            }

                            MetricItem {
                                label: "Enterprise Value"
                                value: formatLargeNumber(getInfoValue("enterpriseValue"))
                            }

                            MetricItem {
                                label: "EV/Revenue"
                                value: formatNumber(getInfoValue("enterpriseToRevenue"), 2)
                            }

                            MetricItem {
                                label: "EV/EBITDA"
                                value: formatNumber(getInfoValue("enterpriseToEbitda"), 2)
                            }
                        }
                    }
                }

                // Financial Health
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: healthColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6

                    ColumnLayout {
                        id: healthColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 12

                        Label {
                            text: "Financial Health"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 3
                            columnSpacing: 16
                            rowSpacing: 12

                            MetricItem {
                                label: "Total Cash"
                                value: formatLargeNumber(getInfoValue("totalCash"))
                            }

                            MetricItem {
                                label: "Total Debt"
                                value: formatLargeNumber(getInfoValue("totalDebt"))
                            }

                            MetricItem {
                                label: "Debt/Equity"
                                value: formatNumber(getInfoValue("debtToEquity"), 2)
                            }

                            MetricItem {
                                label: "Free Cash Flow"
                                value: formatLargeNumber(getInfoValue("freeCashflow"))
                            }

                            MetricItem {
                                label: "Operating CF"
                                value: formatLargeNumber(getInfoValue("operatingCashflow"))
                            }

                            MetricItem {
                                label: "EBITDA"
                                value: formatLargeNumber(getInfoValue("ebitda"))
                            }
                        }
                    }
                }

                // Margins
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: marginsColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6

                    ColumnLayout {
                        id: marginsColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 12

                        Label {
                            text: "Margins & Returns"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 3
                            columnSpacing: 16
                            rowSpacing: 12

                            MetricItem {
                                label: "Gross Margin"
                                value: formatPercent(getInfoValue("grossMargins"))
                            }

                            MetricItem {
                                label: "Operating Margin"
                                value: formatPercent(getInfoValue("operatingMargins"))
                            }

                            MetricItem {
                                label: "EBITDA Margin"
                                value: formatPercent(getInfoValue("ebitdaMargins"))
                            }

                            MetricItem {
                                label: "ROA"
                                value: formatPercent(getInfoValue("returnOnAssets"))
                            }

                            MetricItem {
                                label: "Revenue Growth"
                                value: formatPercent(getInfoValue("revenueGrowth"))
                            }

                            MetricItem {
                                label: "Earnings Growth"
                                value: formatPercent(getInfoValue("earningsGrowth"))
                            }
                        }
                    }
                }

                // Dividends (expanded)
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: dividendColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6
                    visible: getInfoValue("dividendRate") !== null || getInfoValue("dividendYield") !== null

                    ColumnLayout {
                        id: dividendColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 12

                        Label {
                            text: "Dividends"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 4
                            columnSpacing: 16
                            rowSpacing: 12

                            MetricItem {
                                label: "Annual Rate"
                                value: formatPrice(getInfoValue("dividendRate"))
                            }

                            MetricItem {
                                label: "Yield"
                                value: formatPercent(getInfoValue("dividendYield"))
                                valueColor: "#26a69a"
                            }

                            MetricItem {
                                label: "Payout Ratio"
                                value: formatPercent(getInfoValue("payoutRatio"))
                            }

                            MetricItem {
                                label: "Ex-Dividend"
                                value: {
                                    var ts = getInfoValue("exDividendDate")
                                    if (!ts) return "-"
                                    var d = new Date(ts * 1000)
                                    return d.toLocaleDateString()
                                }
                            }
                        }
                    }
                }

                // Short Interest
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: shortColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6
                    visible: getInfoValue("sharesShort") !== null

                    ColumnLayout {
                        id: shortColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 12

                        Label {
                            text: "Short Interest"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 4
                            columnSpacing: 16
                            rowSpacing: 12

                            MetricItem {
                                label: "Shares Short"
                                value: formatLargeNumber(getInfoValue("sharesShort"))
                            }

                            MetricItem {
                                label: "Short Ratio"
                                value: formatNumber(getInfoValue("shortRatio"), 2)
                            }

                            MetricItem {
                                label: "Short % Float"
                                value: formatPercent(getInfoValue("shortPercentOfFloat"))
                                valueColor: {
                                    var pct = getInfoValue("shortPercentOfFloat")
                                    if (pct && pct > 0.1) return "#ef5350"
                                    if (pct && pct > 0.05) return "#ffa726"
                                    return "#e6e6e6"
                                }
                            }

                            MetricItem {
                                label: "Float Shares"
                                value: formatLargeNumber(getInfoValue("floatShares"))
                            }
                        }
                    }
                }

                // Moving Averages & Price
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: maColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6

                    ColumnLayout {
                        id: maColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 12

                        Label {
                            text: "Price & Moving Averages"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 4
                            columnSpacing: 16
                            rowSpacing: 12

                            MetricItem {
                                label: "Current Price"
                                value: formatPrice(getInfoValue("currentPrice"))
                            }

                            MetricItem {
                                label: "Previous Close"
                                value: formatPrice(getInfoValue("previousClose"))
                            }

                            MetricItem {
                                label: "50-Day Avg"
                                value: formatPrice(getInfoValue("fiftyDayAverage"))
                                valueColor: {
                                    var curr = getInfoValue("currentPrice")
                                    var ma = getInfoValue("fiftyDayAverage")
                                    if (curr && ma) return curr > ma ? "#26a69a" : "#ef5350"
                                    return "#e6e6e6"
                                }
                            }

                            MetricItem {
                                label: "200-Day Avg"
                                value: formatPrice(getInfoValue("twoHundredDayAverage"))
                                valueColor: {
                                    var curr = getInfoValue("currentPrice")
                                    var ma = getInfoValue("twoHundredDayAverage")
                                    if (curr && ma) return curr > ma ? "#26a69a" : "#ef5350"
                                    return "#e6e6e6"
                                }
                            }
                        }
                    }
                }

                // Analyst Recommendation
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: recColumn.height + 24
                    color: "#1a1d2e"
                    radius: 6
                    visible: getInfoValue("recommendationKey") !== null

                    ColumnLayout {
                        id: recColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 12

                        Label {
                            text: "Analyst Recommendation"
                            color: "#e6e6e6"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        RowLayout {
                            spacing: 20

                            // Recommendation badge
                            Rectangle {
                                Layout.preferredWidth: recLabel.width + 24
                                Layout.preferredHeight: 32
                                radius: 6
                                color: {
                                    var rec = getInfoValue("recommendationKey")
                                    if (!rec) return "#3d4461"
                                    rec = rec.toLowerCase()
                                    if (rec === "strong_buy" || rec === "strongbuy") return "#26a69a"
                                    if (rec === "buy") return "#4caf50"
                                    if (rec === "hold") return "#ffa726"
                                    if (rec === "sell") return "#ef5350"
                                    if (rec === "strong_sell" || rec === "strongsell") return "#c62828"
                                    return "#3d4461"
                                }

                                Label {
                                    id: recLabel
                                    anchors.centerIn: parent
                                    text: {
                                        var rec = getInfoValue("recommendationKey")
                                        if (!rec) return "-"
                                        return rec.toUpperCase().replace("_", " ")
                                    }
                                    color: "#ffffff"
                                    font.pixelSize: 14
                                    font.bold: true
                                }
                            }

                            MetricItem {
                                label: "Mean Score"
                                value: {
                                    var mean = getInfoValue("recommendationMean")
                                    if (!mean) return "-"
                                    return Number(mean).toFixed(2) + " / 5"
                                }
                            }

                            MetricItem {
                                label: "Analysts"
                                value: {
                                    var n = getInfoValue("numberOfAnalystOpinions")
                                    return n ? String(n) : "-"
                                }
                            }
                        }
                    }
                }

                // Spacer at bottom
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 20
                }
            }
        }
    }

    // Helper functions
    function getInfoValue(field) {
        if (!root.analysisData) return null
        if (!root.analysisData.info) return null
        var value = root.analysisData.info[field]
        return value !== undefined ? value : null
    }

    function formatNumber(value, decimals) {
        if (value === undefined || value === null) return "-"
        return Number(value).toFixed(decimals || 0)
    }

    function formatPrice(value) {
        if (value === undefined || value === null) return "-"
        var currency = "USD"
        if (root.analysisData && root.analysisData.info && root.analysisData.info.currency) {
            currency = root.analysisData.info.currency
        }
        return currency + " " + Number(value).toFixed(2)
    }

    function formatPercent(value) {
        if (value === undefined || value === null) return "-"
        return (Number(value) * 100).toFixed(2) + "%"
    }

    function formatShareCount(value) {
        if (value === undefined || value === null) return "-"
        var num = Number(value)
        if (num >= 1e9) return (num / 1e9).toFixed(2) + "B"
        if (num >= 1e6) return (num / 1e6).toFixed(2) + "M"
        if (num >= 1e3) return (num / 1e3).toFixed(2) + "K"
        return num.toFixed(0)
    }

    function formatLargeNumber(value) {
        if (value === undefined || value === null) return "-"
        var num = Number(value)
        if (num >= 1e12) return (num / 1e12).toFixed(2) + "T"
        if (num >= 1e9) return (num / 1e9).toFixed(2) + "B"
        if (num >= 1e6) return (num / 1e6).toFixed(2) + "M"
        if (num >= 1e3) return (num / 1e3).toFixed(2) + "K"
        return num.toFixed(0)
    }

    // Reusable MetricItem component
    component MetricItem: ColumnLayout {
        property string label: ""
        property string value: "-"
        property color valueColor: "#e6e6e6"

        spacing: 2

        Label {
            text: label
            color: "#6b7280"
            font.pixelSize: 11
        }

        Label {
            text: value
            color: valueColor
            font.pixelSize: 14
            font.bold: true
        }
    }
}
