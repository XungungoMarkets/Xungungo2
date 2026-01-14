// chart.js (enhanced with AdvancedRenderer)
// Requiere:
//  - LightweightCharts v5+
//  - qwebchannel.js
//  - advanced_renderer.js (sistema genérico)

// Chart Manager Module - Encapsulates all chart state and functionality
const ChartManager = (function() {
  'use strict';

  // Private state
  let chart = null;
  let candleSeries = null;
  const lineSeries = new Map();
  const markerPlugins = new Map();
  let advancedRenderer = null;
  let currentSeriesDefs = [];

  // Constants
  const QWEBCHANNEL_INIT_DELAY_MS = 100;

  // Private utility functions
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

      candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
        upColor: "#26a69a",
        downColor: "#ef5350",
        borderVisible: false,
        wickUpColor: "#26a69a",
        wickDownColor: "#ef5350",
      });

      // Inicializar sistema de renderizado avanzado
      if (typeof window.AdvancedRenderer === "function") {
        advancedRenderer = new window.AdvancedRenderer();
        console.log("AdvancedRenderer initialized");
      } else {
        console.warn("AdvancedRenderer no disponible. ¿Cargaste advanced_renderer.js?");
      }

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

  function getColorForSeries(id) {
    const colors = ["#2196F3", "#FF9800", "#4CAF50", "#9C27B0", "#F44336"];
    const hash = id.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  }

  function ensureLineSeries(id) {
    if (lineSeries.has(id)) return lineSeries.get(id);

    try {
      const s = chart.addSeries(LightweightCharts.LineSeries, {
        lineWidth: 2,
        color: getColorForSeries(id),
      });
      lineSeries.set(id, s);
      console.log("Created line series:", id);
      return s;
    } catch (err) {
      console.error("Error creating line series:", err);
      return null;
    }
  }

  function ensureMarkerPlugin(seriesId) {
    if (markerPlugins.has(seriesId)) {
      console.log(`MarkerPlugin: Reusing existing plugin for ${seriesId}`);
      return markerPlugins.get(seriesId);
    }

    console.log(`MarkerPlugin: Attempting to create plugin for ${seriesId}`);
    console.log("  LightweightCharts.createSeriesMarkers:", typeof LightweightCharts.createSeriesMarkers);
    console.log("  window.createSeriesMarkers:", typeof window.createSeriesMarkers);
    console.log("  window.SeriesMarkers:", typeof window.SeriesMarkers);

    const createSeriesMarkers = (
      typeof LightweightCharts.createSeriesMarkers === "function"
        ? LightweightCharts.createSeriesMarkers
        : (typeof window.createSeriesMarkers === "function"
          ? window.createSeriesMarkers
          : (LightweightCharts.SeriesMarkers && typeof LightweightCharts.SeriesMarkers.createSeriesMarkers === "function"
            ? LightweightCharts.SeriesMarkers.createSeriesMarkers
            : (window.SeriesMarkers && typeof window.SeriesMarkers.createSeriesMarkers === "function"
              ? window.SeriesMarkers.createSeriesMarkers
              : null)))
    );

    if (!createSeriesMarkers) {
      console.error("MarkerPlugin: series-markers.js not loaded or API not available");
      return null;
    }

    console.log("  createSeriesMarkers function found:", typeof createSeriesMarkers);

    const series = seriesId === "candles" ? candleSeries : ensureLineSeries(seriesId);
    if (!series) {
      console.error(`MarkerPlugin: Target series ${seriesId} not found`);
      return null;
    }

    try {
      const plugin = createSeriesMarkers(series, []);
      markerPlugins.set(seriesId, plugin);
      console.log(`MarkerPlugin: Successfully created plugin for ${seriesId}`);
      return plugin;
    } catch (err) {
      console.error(`MarkerPlugin: Error creating plugin for ${seriesId}:`, err);
      return null;
    }
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

  function setIndicators(indicators, seriesDefs) {
    if (!chart) {
      console.warn("Chart not initialized");
      return;
    }

    try {
      // Store series definitions for advanced rendering
      currentSeriesDefs = seriesDefs || [];

      // Build set of series IDs that should exist based on seriesDefs
      const expectedSeriesIds = new Set();
      for (const def of currentSeriesDefs) {
        if (def.type === "line" && def.id) {
          expectedSeriesIds.add(def.id);
        } else if (def.type === "fill_between") {
          // fill_between creates line series for series1 and series2
          if (def.series1) expectedSeriesIds.add(def.series1);
          if (def.series2) expectedSeriesIds.add(def.series2);
        } else if (def.type === "markers") {
          if (def.series && def.series !== "candles") expectedSeriesIds.add(def.series);
        } else if (def.type === "band") {
          // band creates a host series
          const hostSeriesId = `${def.id}_host`;
          expectedSeriesIds.add(hostSeriesId);
        }
      }

      // Remove series that are no longer in the definitions
      for (const [id, s] of lineSeries.entries()) {
        if (!expectedSeriesIds.has(id)) {
          console.log("Removing series:", id);
          if (markerPlugins.has(id)) {
            markerPlugins.delete(id);
          }
          chart.removeSeries(s);
          lineSeries.delete(id);
        }
      }

      // Clean up primitives when indicators are cleared or changed
      if (advancedRenderer && (!indicators || Object.keys(indicators).length === 0)) {
        console.log("Clearing all primitives");
        advancedRenderer.clear();
      }

      if (!indicators) return;

      // 1) Renderizar líneas básicas
      const basicSeries = currentSeriesDefs.filter(
        (def) => def.type === "line" && def.column
      );

      console.log(`Found ${basicSeries.length} basic line series to render`);

      for (const def of basicSeries) {
        const id = def.id;
        const data = indicators[def.column];

        if (!data) {
          console.warn(`No data for column ${def.column}`);
          continue;
        }

        const s = ensureLineSeries(id);
        if (s) {
          console.log(`Setting ${data.length} points for series ${id}`);
          s.setData(data);
        }
      }

      // 1b) Apply markers
      const markerDefs = currentSeriesDefs.filter(
        (def) => def.type === "markers" && def.series && def.column
      );

      const markerSeriesIds = new Set(markerDefs.map((def) => def.series));
      for (const [id, plugin] of markerPlugins.entries()) {
        if (!markerSeriesIds.has(id) && plugin && typeof plugin.setMarkers === "function") {
          plugin.setMarkers([]);
        }
      }

      for (const def of markerDefs) {
        console.log(`Processing marker definition:`, def);

        const markerPlugin = ensureMarkerPlugin(def.series);
        if (!markerPlugin) {
          console.warn(`Skipping markers for ${def.id}: plugin not available`);
          continue;
        }

        const data = indicators[def.column] || [];
        console.log(`Marker data for ${def.id}: ${data.length} points from column ${def.column}`);

        if (data.length === 0) {
          console.warn(`No data for marker column ${def.column}`);
          markerPlugin.setMarkers([]);
          continue;
        }

        const upColor = def.upColor || "#26a69a";
        const downColor = def.downColor || "#ef5350";
        const shapeUp = def.shapeUp || "arrowUp";
        const shapeDown = def.shapeDown || "arrowDown";
        const textUp = def.textUp || "UP";
        const textDown = def.textDown || "DOWN";

        const markers = data.map((p) => {
          const isUp = p.value >= 0;
          return {
            time: p.time,
            position: isUp ? "belowBar" : "aboveBar",
            color: isUp ? upColor : downColor,
            shape: isUp ? shapeUp : shapeDown,
            text: isUp ? textUp : textDown,
          };
        });

        console.log(`Setting ${markers.length} markers on series ${def.series}`);
        console.log(`First marker:`, markers[0]);

        try {
          markerPlugin.setMarkers(markers);
          console.log(`Successfully set markers for ${def.id}`);
        } catch (err) {
          console.error(`Error setting markers for ${def.id}:`, err);
        }
      }

      // 2) Aplicar renderizado avanzado (fill_between, band, etc.)
      if (advancedRenderer) {
        const advancedDefs = currentSeriesDefs.filter(
          (def) => def.type === "fill_between" || def.type === "band"
        );

        console.log(`Found ${advancedDefs.length} advanced series to render`);
        console.log("Advanced defs:", JSON.stringify(advancedDefs, null, 2));
        console.log("Available indicators:", Object.keys(indicators));

        // Get current primitive IDs
        const currentPrimitiveIds = new Set(advancedDefs.map(def => def.id));

        // Remove primitives that are no longer in the definitions
        advancedRenderer.removeUnused(currentPrimitiveIds);

        // Apply the current advanced definitions (pass candleSeries for price coordinate reference)
        advancedRenderer.apply(chart, ensureLineSeries, advancedDefs, indicators, candleSeries);
      }
    } catch (err) {
      console.error("Error setting indicators:", err);
    }
  }

  // Public API
  return {
    init: initChart,
    setCandles: setCandles,
    setIndicators: setIndicators,
    showOverlay: showOverlay,
    hideOverlay: hideOverlay
  };
})();

document.addEventListener("DOMContentLoaded", () => {
  console.log("=== DOM LOADED ===");
  console.log("QWebChannel available:", typeof QWebChannel !== "undefined");
  console.log("qt available:", typeof qt !== "undefined");

  const ok = ChartManager.init();

  if (typeof QWebChannel === "undefined") {
    ChartManager.showOverlay("QWebChannel no disponible");
    return;
  }

  if (typeof qt === "undefined") {
    ChartManager.showOverlay("Objeto 'qt' no disponible");
    return;
  }

  console.log("=== INITIALIZING QWEBCHANNEL ===");

  // Use constant from ChartManager module
  setTimeout(function () {
    console.log("Attempting QWebChannel initialization...");

    new QWebChannel(qt.webChannelTransport, function (channel) {
      console.log("QWebChannel callback invoked");
      console.log("Channel:", channel);
      console.log("Channel.objects:", channel.objects);

      const objectKeys = Object.keys(channel.objects);
      console.log("Object.keys():", objectKeys);
      console.log("Object.keys() length:", objectKeys.length);

      console.log("Trying direct access to chartBridge...");
      console.log("channel.objects.chartBridge:", channel.objects.chartBridge);
      console.log("channel.objects['chartBridge']:", channel.objects["chartBridge"]);

      const bridge = channel.objects.chartBridge;
      console.log("bridge assigned:", bridge);

      if (!bridge) {
        const availableKeys = [];
        for (const key in channel.objects) {
          availableKeys.push(key);
          console.log("  - Property:", key, "=", channel.objects[key]);
        }
        ChartManager.showOverlay(
          "chartBridge no está registrado.\nObjetos disponibles: " +
            availableKeys.join(", ")
        );
        return;
      }

      console.log("chartBridge found! Type:", typeof bridge);
      console.log("bridge properties:", Object.keys(bridge));

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

      if (bridge.push) {
        console.log("bridge.push exists, type:", typeof bridge.push);
        if (typeof bridge.push.connect === "function") {
          bridge.push.connect(function (payload) {
            console.log("=== RECEIVED PUSH ===");
            console.log("Payload length:", payload.length);

            if (!ok) {
              console.warn("Chart not initialized, ignoring");
              return;
            }

            try {
              const msg = JSON.parse(payload);

              // Validate message structure
              if (!msg || typeof msg !== 'object') {
                console.error("Invalid message format: expected object");
                return;
              }

              if (!msg.type) {
                console.error("Invalid message: missing 'type' field");
                return;
              }

              console.log("Message type:", msg.type);
              console.log("Candles:", msg.candles ? msg.candles.length : 0);
              console.log(
                "Indicators:",
                msg.indicators ? Object.keys(msg.indicators) : []
              );
              console.log(
                "Series defs:",
                msg.seriesDefs ? msg.seriesDefs.length : 0
              );

              if (msg.type === "all") {
                // Validate candles structure
                if (!Array.isArray(msg.candles)) {
                  console.error("Invalid 'candles': expected array");
                  return;
                }
                if (!msg.indicators || typeof msg.indicators !== 'object') {
                  console.error("Invalid 'indicators': expected object");
                  return;
                }
                if (!Array.isArray(msg.seriesDefs)) {
                  console.error("Invalid 'seriesDefs': expected array");
                  return;
                }

                ChartManager.setCandles(msg.candles);
                ChartManager.setIndicators(msg.indicators, msg.seriesDefs);
              } else if (msg.type === "indicators") {
                // Validate indicators structure
                if (!msg.indicators || typeof msg.indicators !== 'object') {
                  console.error("Invalid 'indicators': expected object");
                  return;
                }
                if (!Array.isArray(msg.seriesDefs)) {
                  console.error("Invalid 'seriesDefs': expected array");
                  return;
                }

                ChartManager.setIndicators(msg.indicators, msg.seriesDefs);
              } else {
                console.warn("Unknown message type:", msg.type);
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
  }, 100);
});
