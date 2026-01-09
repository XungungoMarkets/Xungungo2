let chart;
let candleSeries;
const indicatorSeries = {};

function initChart() {
  const container = document.getElementById('chart');
  chart = LightweightCharts.createChart(container, {
    layout: {
      background: { color: '#ffffff' },
      textColor: '#1e1e1e',
    },
    rightPriceScale: { borderColor: '#d1d4dc' },
    timeScale: { borderColor: '#d1d4dc' },
  });

  candleSeries = chart.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderVisible: false,
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
  });
}

function reset() {
  if (!chart) {
    return;
  }
  candleSeries.setData([]);
  Object.values(indicatorSeries).forEach(series => {
    chart.removeSeries(series);
  });
  Object.keys(indicatorSeries).forEach(key => delete indicatorSeries[key]);
}

function setCandles(data) {
  if (!chart) {
    initChart();
  }
  candleSeries.setData(data);
  chart.timeScale().fitContent();
}

function setIndicatorSeries(seriesId, data) {
  if (!chart) {
    initChart();
  }
  if (!indicatorSeries[seriesId]) {
    indicatorSeries[seriesId] = chart.addLineSeries({
      lineWidth: 2,
    });
  }
  indicatorSeries[seriesId].setData(data);
}

function setIndicatorVisible(seriesId, visible) {
  if (!indicatorSeries[seriesId]) {
    return;
  }
  indicatorSeries[seriesId].applyOptions({ visible: visible });
}

window.onQtWebChannelReady = function () {
  new QWebChannel(qt.webChannelTransport, function (channel) {
    window.bridge = channel.objects.chartBridge;
    bridge.setCandles.connect(function (payload) {
      setCandles(JSON.parse(payload));
    });
    bridge.setIndicatorSeries.connect(function (seriesId, payload) {
      setIndicatorSeries(seriesId, JSON.parse(payload));
    });
    bridge.setIndicatorVisible.connect(function (seriesId, visible) {
      setIndicatorVisible(seriesId, visible);
    });
    bridge.reset.connect(function () {
      reset();
    });
    if (bridge.onReady) {
      bridge.onReady();
    }
  });
};
