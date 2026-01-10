let chart;
let candleSeries;
const lineSeries = new Map();

function showOverlay(msg) {
  console.log("OVERLAY:", msg);
  const o = document.getElementById("overlay");
  if (!o) {
    console.error("Overlay element not found!");
    return;
  }
  o.style.display = "flex";
  o.textContent = msg;
}

function hideOverlay() {
  const o = document.getElementById("overlay");
  if (o) o.style.display = "none";
}

function initChart() {
  console.log("=== INITIALIZING CHART ===");
  console.log("LightweightCharts available:", typeof LightweightCharts !== "undefined");
  
  if (typeof LightweightCharts === "undefined") {
    showOverlay(
      "No se pudo cargar LightweightCharts.\n" +
      "Si tu red bloquea CDN, descarga el archivo standalone."
    );
    return false;
  }

  console.log("LightweightCharts.createChart:", typeof LightweightCharts.createChart);
  
  if (typeof LightweightCharts.createChart !== "function") {
    showOverlay("LightweightCharts API no disponible.");
    return false;
  }

  const el = document.getElementById("chart");
  if (!el) {
    showOverlay("Elemento #chart no encontrado");
    return false;
  }

  try {
    chart = LightweightCharts.createChart(el, {
      layout: { background: { color: "#0b0d14" }, textColor: "#e6e6e6" },
      grid: { vertLines: { color: "#1b2030" }, horzLines: { color: "#1b2030" } },
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: "#2d3345" },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    });

    // v5+ API uses addSeries with type parameter
    candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    });

    window.addEventListener("resize", () => {
      if (chart && el) {
        chart.resize(el.clientWidth, el.clientHeight);
      }
    });

    console.log("Chart initialized successfully!");
    hideOverlay();
    return true;
  } catch (err) {
    showOverlay("Error al inicializar: " + err.message);
    console.error("Chart init error:", err);
    return false;
  }
}

function ensureLineSeries(id) {
  if (lineSeries.has(id)) return lineSeries.get(id);
  
  try {
    const s = chart.addSeries(LightweightCharts.LineSeries, { 
      lineWidth: 2,
      color: getColorForSeries(id)
    });
    lineSeries.set(id, s);
    console.log("Created line series:", id);
    return s;
  } catch (err) {
    console.error("Error creating line series:", err);
    return null;
  }
}

function getColorForSeries(id) {
  const colors = ["#2196F3", "#FF9800", "#4CAF50", "#9C27B0", "#F44336"];
  const hash = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

function setCandles(data) {
  if (!candleSeries) {
    console.warn("Candle series not initialized");
    return;
  }
  
  try {
    console.log("Setting", data.length, "candles");
    candleSeries.setData(data);
  } catch (err) {
    console.error("Error setting candles:", err);
  }
}

function setIndicators(indicators) {
  if (!chart) {
    console.warn("Chart not initialized");
    return;
  }

  try {
    // Remove series that no longer exist
    for (const [id, s] of lineSeries.entries()) {
      if (!indicators || !Object.prototype.hasOwnProperty.call(indicators, id)) {
        console.log("Removing series:", id);
        chart.removeSeries(s);
        lineSeries.delete(id);
      }
    }

    if (!indicators) return;

    // Update existing and create new series
    for (const id of Object.keys(indicators)) {
      const s = ensureLineSeries(id);
      if (s && indicators[id]) {
        console.log("Setting", indicators[id].length, "points for", id);
        s.setData(indicators[id]);
      }
    }
  } catch (err) {
    console.error("Error setting indicators:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("=== DOM LOADED ===");
  console.log("QWebChannel available:", typeof QWebChannel !== "undefined");
  console.log("qt available:", typeof qt !== "undefined");
  
  const ok = initChart();
  
  if (typeof QWebChannel === "undefined") {
    showOverlay("QWebChannel no disponible");
    return;
  }

  if (typeof qt === "undefined") {
    showOverlay("Objeto 'qt' no disponible");
    return;
  }

  console.log("=== INITIALIZING QWEBCHANNEL ===");
  
  // Add a small delay to ensure Qt side is ready
  setTimeout(function() {
    console.log("Attempting QWebChannel initialization...");
    
    new QWebChannel(qt.webChannelTransport, function(channel) {
      console.log("QWebChannel callback invoked");
      console.log("Channel:", channel);
      console.log("Channel.objects:", channel.objects);
      
      // Qt WebChannel objects may not be enumerable, try direct access
      const objectKeys = Object.keys(channel.objects);
      console.log("Object.keys():", objectKeys);
      console.log("Object.keys() length:", objectKeys.length);
      
      // Try direct property access
      console.log("Trying direct access to chartBridge...");
      console.log("channel.objects.chartBridge:", channel.objects.chartBridge);
      console.log("channel.objects['chartBridge']:", channel.objects['chartBridge']);

      const bridge = channel.objects.chartBridge;
      console.log("bridge assigned:", bridge);
      
      if (!bridge) {
        const availableKeys = [];
        for (const key in channel.objects) {
          availableKeys.push(key);
          console.log("  - Property:", key, "=", channel.objects[key]);
        }
        showOverlay("chartBridge no está registrado.\nObjetos disponibles: " + availableKeys.join(", "));
        return;
      }

      console.log("chartBridge found! Type:", typeof bridge);
      console.log("bridge properties:", Object.keys(bridge));
      
      // Check if ready method exists
      if (typeof bridge.ready === "function") {
        console.log("Calling bridge.ready()...");
        try {
          bridge.ready();
          console.log("bridge.ready() called successfully");
        } catch (err) {
          console.error("Error calling bridge.ready():", err);
        }
      } else {
        console.warn("bridge.ready is not a function, type:", typeof bridge.ready);
      }

      // Connect to push signal
      if (bridge.push) {
        console.log("bridge.push exists, type:", typeof bridge.push);
        if (typeof bridge.push.connect === "function") {
          bridge.push.connect(function(payload) {
            console.log("=== RECEIVED PUSH ===");
            console.log("Payload length:", payload.length);
            
            if (!ok) {
              console.warn("Chart not initialized, ignoring");
              return;
            }

            try {
              const msg = JSON.parse(payload);
              console.log("Message type:", msg.type);
              console.log("Candles:", msg.candles ? msg.candles.length : 0);
              console.log("Indicators:", msg.indicators ? Object.keys(msg.indicators) : []);
              
              if (msg.type === "all") {
                setCandles(msg.candles || []);
                setIndicators(msg.indicators || {});
              } else if (msg.type === "indicators") {
                setIndicators(msg.indicators || {});
              }
            } catch (err) {
              console.error("Error processing push:", err);
            }
          });
          console.log("Connected to bridge.push signal");
        } else {
          console.error("bridge.push.connect is not a function");
        }
      } else {
        console.error("bridge.push does not exist");
      }
    });
  }, 100); // Wait 100ms for Qt to be ready
});