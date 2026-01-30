// chart.js (enhanced with AdvancedRenderer)
// Requiere:
//  - LightweightCharts v5+
//  - qwebchannel.js
//  - advanced_renderer.js (sistema genérico)

const DEBUG = true; // Force debug for troubleshooting
const log = (...args) => {
  if (DEBUG) console["log"](...args);
};
const warn = (...args) => {
  if (DEBUG) console["warn"](...args);
};
const QWEBCHANNEL_INIT_DELAY_MS = 100;

// Global flags to prevent multiple initializations
let qwebchannelInitialized = false;
let qwebchannelInitializing = false;

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
  let lastCandle = null;  // Track last candle for realtime updates
  let candleIntervalSeconds = 0;  // Interval between candles in seconds
  let extendedHoursPriceLine = null;  // Price line for post/pre market
  let extendedHoursLabelPrimitive = null;  // Label primitive for post/pre market
  let currentMarketStatus = "";  // Current market status
  let lastExtendedHoursPrice = null;  // Track last price to avoid unnecessary updates
  let lastExtendedHoursColor = null;  // Track last color to detect status changes

  // Private utility functions
  function showOverlay(msg) {
    log("OVERLAY:", msg);
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
    log("=== INITIALIZING CHART ===");
    log("LightweightCharts available:", typeof LightweightCharts !== "undefined");

    if (typeof LightweightCharts === "undefined") {
      showOverlay(
        "No se pudo cargar LightweightCharts.\n" +
          "Si tu red bloquea CDN, descarga el archivo standalone."
      );
      return false;
    }

    log("LightweightCharts.createChart:", typeof LightweightCharts.createChart);

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
        log("AdvancedRenderer initialized");
      } else {
        warn("AdvancedRenderer no disponible. ¿Cargaste advanced_renderer.js?");
      }

      window.addEventListener("resize", () => {
        if (chart && el) {
          chart.resize(el.clientWidth, el.clientHeight);
        }
      });

      log("Chart initialized successfully!");
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

  function ensureLineSeries(id, options) {
    if (lineSeries.has(id)) {
      // If series exists and options provided, update options
      if (options) {
        const s = lineSeries.get(id);
        try {
          s.applyOptions(options);
        } catch (err) {
          warn(`Error applying options to series ${id}:`, err);
        }
      }
      return lineSeries.get(id);
    }

    try {
      const defaultOpts = {
        lineWidth: 2,
        color: getColorForSeries(id),
      };
      const mergedOpts = options ? { ...defaultOpts, ...options } : defaultOpts;

      const s = chart.addSeries(LightweightCharts.LineSeries, mergedOpts);
      lineSeries.set(id, s);
      log("Created line series:", id, "with options:", mergedOpts);
      return s;
    } catch (err) {
      console.error("Error creating line series:", err);
      return null;
    }
  }

  function ensureMarkerPlugin(seriesId) {
    if (markerPlugins.has(seriesId)) {
      log(`MarkerPlugin: Reusing existing plugin for ${seriesId}`);
      return markerPlugins.get(seriesId);
    }

    log(`MarkerPlugin: Attempting to create plugin for ${seriesId}`);
    log("  LightweightCharts.createSeriesMarkers:", typeof LightweightCharts.createSeriesMarkers);
    log("  window.createSeriesMarkers:", typeof window.createSeriesMarkers);
    log("  window.SeriesMarkers:", typeof window.SeriesMarkers);

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

    log("  createSeriesMarkers function found:", typeof createSeriesMarkers);

    const series = seriesId === "candles" ? candleSeries : ensureLineSeries(seriesId);
    if (!series) {
      console.error(`MarkerPlugin: Target series ${seriesId} not found`);
      return null;
    }

    try {
      const plugin = createSeriesMarkers(series, []);
      markerPlugins.set(seriesId, plugin);
      log(`MarkerPlugin: Successfully created plugin for ${seriesId}`);
      return plugin;
    } catch (err) {
      console.error(`MarkerPlugin: Error creating plugin for ${seriesId}:`, err);
      return null;
    }
  }

  function setCandles(data) {
    if (!candleSeries) {
      warn("Candle series not initialized");
      return;
    }

    try {
      log("Setting", data.length, "candles");

      // Clear extended hours line and label when loading new data
      if (extendedHoursPriceLine) {
        try {
          candleSeries.removePriceLine(extendedHoursPriceLine);
        } catch (e) {
          // Ignore
        }
        extendedHoursPriceLine = null;
      }
      if (extendedHoursLabelPrimitive) {
        extendedHoursLabelPrimitive.setEnabled(false);
      }
      currentMarketStatus = "";
      lastExtendedHoursPrice = null;
      lastExtendedHoursColor = null;

      candleSeries.setData(data);

      // Store last candle for realtime updates
      if (data.length > 0) {
        lastCandle = { ...data[data.length - 1] };
        log("Last candle stored:", lastCandle);

        // Calculate candle interval from last two candles
        if (data.length >= 2) {
          const secondLast = data[data.length - 2];
          candleIntervalSeconds = lastCandle.time - secondLast.time;
          log("Candle interval calculated:", candleIntervalSeconds, "seconds");
        }
      }
    } catch (err) {
      console.error("Error setting candles:", err);
    }
  }

  function setIndicators(indicators, seriesDefs) {
    if (!chart) {
      warn("Chart not initialized");
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
        } else if (def.type === "horizontal_lines") {
          // horizontal_lines creates a host series
          const hostSeriesId = `${def.id}_host`;
          expectedSeriesIds.add(hostSeriesId);
        }
      }

      // Remove series that are no longer in the definitions
      for (const [id, s] of lineSeries.entries()) {
        if (!expectedSeriesIds.has(id)) {
          log("Removing series:", id);
          if (markerPlugins.has(id)) {
            markerPlugins.delete(id);
          }
          chart.removeSeries(s);
          lineSeries.delete(id);
        }
      }

      // Clean up primitives when indicators are cleared or changed
      if (advancedRenderer && (!indicators || Object.keys(indicators).length === 0)) {
        log("Clearing all primitives");
        advancedRenderer.clear();
      }

      if (!indicators) return;

      // 1) Renderizar líneas básicas
      const basicSeries = currentSeriesDefs.filter(
        (def) => def.type === "line" && def.column
      );

      log(`Found ${basicSeries.length} basic line series to render`);

      for (const def of basicSeries) {
        const id = def.id;
        const data = indicators[def.column];

        if (!data) {
          warn(`No data for column ${def.column}`);
          continue;
        }

        // Build series options from definition
        const seriesOpts = {};
        if (def.color) seriesOpts.color = def.color;
        if (def.lineWidth) seriesOpts.lineWidth = def.lineWidth;
        if (def.lineStyle) seriesOpts.lineStyle = def.lineStyle;
        if (def.lineType) seriesOpts.lineType = def.lineType;
        if (def.lastValueVisible !== undefined) seriesOpts.lastValueVisible = def.lastValueVisible;
        if (def.priceLineVisible !== undefined) seriesOpts.priceLineVisible = def.priceLineVisible;

        const s = ensureLineSeries(id, Object.keys(seriesOpts).length > 0 ? seriesOpts : null);
        if (s) {
          log(`Setting ${data.length} points for series ${id}`);
          s.setData(data);
        }
      }

      // 1b) Apply markers - Group all markers by series before setting
      const markerDefs = currentSeriesDefs.filter(
        (def) => def.type === "markers" && def.series && def.column
      );

      const markerSeriesIds = new Set(markerDefs.map((def) => def.series));
      for (const [id, plugin] of markerPlugins.entries()) {
        if (!markerSeriesIds.has(id) && plugin && typeof plugin.setMarkers === "function") {
          plugin.setMarkers([]);
        }
      }

      // Group markers by series to avoid overwriting
      const markersBySeries = new Map();

      for (const def of markerDefs) {
        log(`Processing marker definition:`, def);

        const data = indicators[def.column] || [];
        log(`Marker data for ${def.id}: ${data.length} points from column ${def.column}`);

        if (data.length === 0) {
          continue;
        }

        const upColor = def.upColor || "#26a69a";
        const downColor = def.downColor || "#ef5350";
        const shapeUp = def.shapeUp || "arrowUp";
        const shapeDown = def.shapeDown || "arrowDown";
        const textUp = def.textUp || "UP";
        const textDown = def.textDown || "DOWN";
        const markerSize = def.size || 1;

        const markers = data.map((p) => {
          const isUp = p.value >= 0;
          return {
            time: p.time,
            position: isUp ? "belowBar" : "aboveBar",
            color: isUp ? upColor : downColor,
            shape: isUp ? shapeUp : shapeDown,
            text: isUp ? textUp : textDown,
            size: markerSize,
          };
        });

        // Accumulate markers for this series
        if (!markersBySeries.has(def.series)) {
          markersBySeries.set(def.series, []);
        }
        markersBySeries.get(def.series).push(...markers);
      }

      // Now set all markers for each series at once
      for (const [seriesId, allMarkers] of markersBySeries.entries()) {
        const markerPlugin = ensureMarkerPlugin(seriesId);
        if (!markerPlugin) {
          warn(`Skipping markers for series ${seriesId}: plugin not available`);
          continue;
        }

        // Sort markers by time to ensure proper ordering
        allMarkers.sort((a, b) => a.time - b.time);

        log(`Setting ${allMarkers.length} total markers on series ${seriesId}`);

        try {
          markerPlugin.setMarkers(allMarkers);
          log(`Successfully set markers for series ${seriesId}`);
        } catch (err) {
          console.error(`Error setting markers for series ${seriesId}:`, err);
        }
      }

      // 2) Aplicar renderizado avanzado (fill_between, band, horizontal_lines, etc.)
      if (advancedRenderer) {
        const advancedDefs = currentSeriesDefs.filter(
          (def) => def.type === "fill_between" || def.type === "band" || def.type === "horizontal_lines"
        );

        log(`Found ${advancedDefs.length} advanced series to render`);
        log("Advanced defs:", JSON.stringify(advancedDefs, null, 2));
        log("Available indicators:", Object.keys(indicators));

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

  // Update or remove extended hours price line (post/pre market)
  function updateExtendedHoursLine(price, marketStatus) {
    if (!candleSeries) return;

    // Check for extended hours (handle both formats: "After Hours" and "After-Hours")
    const isPostMarket = marketStatus === "After Hours" || marketStatus === "After-Hours";
    const isPreMarket = marketStatus === "Pre-Market" || marketStatus === "Pre Market";
    const isExtendedHours = isPostMarket || isPreMarket;

    // Determine label based on market status
    let labelPrefix = "";
    let lineColor = "#2962FF";  // Blue color like TradingView

    if (isPostMarket) {
      labelPrefix = "Post";
    } else if (isPreMarket) {
      labelPrefix = "Pre";
      lineColor = "#FF9800";  // Orange for pre-market
    }

    // Remove existing line and label if market is open or closed (not extended hours)
    if (!isExtendedHours) {
      if (extendedHoursPriceLine) {
        try {
          candleSeries.removePriceLine(extendedHoursPriceLine);
        } catch (e) {
          // Line may not exist
        }
        extendedHoursPriceLine = null;
        lastExtendedHoursPrice = null;
        lastExtendedHoursColor = null;
      }
      if (extendedHoursLabelPrimitive) {
        extendedHoursLabelPrimitive.setEnabled(false);
      }
      return;
    }

    // Optimization: Skip update if price hasn't changed significantly (< $0.01)
    const priceThreshold = 0.01;
    const colorChanged = lastExtendedHoursColor !== lineColor;
    const priceChanged = lastExtendedHoursPrice === null ||
                         Math.abs(price - lastExtendedHoursPrice) >= priceThreshold;

    if (!priceChanged && !colorChanged && extendedHoursPriceLine && extendedHoursLabelPrimitive) {
      return; // No significant change, skip update
    }

    // Format price for display
    const formattedPrice = price.toFixed(2);
    const axisLabel = `${labelPrefix} ${formattedPrice}`;

    try {
      // Only recreate price line if color changed or line doesn't exist
      if (colorChanged || !extendedHoursPriceLine) {
        if (extendedHoursPriceLine) {
          try {
            candleSeries.removePriceLine(extendedHoursPriceLine);
          } catch (e) {
            // Ignore
          }
        }
        extendedHoursPriceLine = candleSeries.createPriceLine({
          price: price,
          color: lineColor,
          lineWidth: 1,
          lineStyle: LightweightCharts.LineStyle.Dashed,
          lineVisible: true,
          axisLabelVisible: false,
        });
      } else {
        // Just update the price on existing line
        extendedHoursPriceLine.applyOptions({ price: price });
      }

      // Create primitive if needed
      if (!extendedHoursLabelPrimitive && typeof window.PriceAxisLabelPrimitive === "function") {
        extendedHoursLabelPrimitive = new window.PriceAxisLabelPrimitive();
        candleSeries.attachPrimitive(extendedHoursLabelPrimitive);
      }

      // Update primitive
      if (extendedHoursLabelPrimitive) {
        extendedHoursLabelPrimitive.setEnabled(true);
        extendedHoursLabelPrimitive.setPrice(price);
        extendedHoursLabelPrimitive.setText(axisLabel);
        if (colorChanged) {
          extendedHoursLabelPrimitive.setColors(lineColor, "#FFFFFF");
        }
      }

      // Track last values
      lastExtendedHoursPrice = price;
      lastExtendedHoursColor = lineColor;

    } catch (err) {
      warn("Error updating extended hours price line:", err.message);
    }
  }

  // Update last candle with realtime price
  function updateRealtimePrice(price, marketStatus) {
    if (!candleSeries) {
      warn("Candle series not initialized for realtime update");
      return;
    }

    // Update market status
    currentMarketStatus = marketStatus || "";

    // Always update extended hours line
    updateExtendedHoursLine(price, currentMarketStatus);

    // Only update candles during regular market hours
    const isExtendedHours = currentMarketStatus === "After Hours" || currentMarketStatus === "After-Hours" ||
                            currentMarketStatus === "Pre-Market" || currentMarketStatus === "Pre Market";

    if (isExtendedHours) {
      log("Extended hours - showing price line only, not updating candle");
      return;
    }

    if (!lastCandle) {
      warn("No last candle available for realtime update");
      return;
    }

    if (!candleIntervalSeconds || candleIntervalSeconds <= 0) {
      warn("Candle interval not set, cannot determine current period");
      return;
    }

    try {
      // Get current time in seconds (UTC)
      const nowSeconds = Math.floor(Date.now() / 1000);

      // Calculate which candle period we should be in
      // Floor the current time to the nearest interval boundary
      const currentPeriodStart = Math.floor(nowSeconds / candleIntervalSeconds) * candleIntervalSeconds;

      // Check if we need to create a new candle
      if (currentPeriodStart > lastCandle.time) {
        // We've moved to a new period - create a new candle
        const newCandle = {
          time: currentPeriodStart,
          open: price,
          high: price,
          low: price,
          close: price
        };

        candleSeries.update(newCandle);
        lastCandle = { ...newCandle };

        log("New candle created at", currentPeriodStart, "price:", price);
      } else {
        // Update existing candle
        const updatedCandle = {
          time: lastCandle.time,
          open: lastCandle.open,
          high: Math.max(lastCandle.high, price),
          low: Math.min(lastCandle.low, price),
          close: price
        };

        candleSeries.update(updatedCandle);

        // Update our stored last candle
        lastCandle.high = updatedCandle.high;
        lastCandle.low = updatedCandle.low;
        lastCandle.close = price;

        log("Realtime price updated:", price, "candle time:", lastCandle.time);
      }
    } catch (err) {
      warn("Error updating realtime price:", err.message);
    }
  }

  // Public API
  return {
    init: initChart,
    setCandles: setCandles,
    setIndicators: setIndicators,
    updateRealtimePrice: updateRealtimePrice,
    showOverlay: showOverlay,
    hideOverlay: hideOverlay
  };
})();

document.addEventListener("DOMContentLoaded", () => {
  log("=== DOM LOADED ===");
  log("QWebChannel available:", typeof QWebChannel !== "undefined");
  log("qt available:", typeof qt !== "undefined");

  const ok = ChartManager.init();

  if (typeof QWebChannel === "undefined") {
    ChartManager.showOverlay("QWebChannel no disponible");
    return;
  }

  if (typeof qt === "undefined") {
    ChartManager.showOverlay("Objeto 'qt' no disponible");
    return;
  }

  log("=== INITIALIZING QWEBCHANNEL ===");

  // Prevent multiple initializations
  if (qwebchannelInitialized || qwebchannelInitializing) {
    log("QWebChannel already initialized or initializing, skipping");
    return;
  }
  qwebchannelInitializing = true;

  // Use constant from ChartManager module
  setTimeout(function () {
    // Double-check in case of race condition
    if (qwebchannelInitialized) {
      log("QWebChannel already initialized during delay, skipping");
      qwebchannelInitializing = false;
      return;
    }

    log("Attempting QWebChannel initialization...");

    new QWebChannel(qt.webChannelTransport, function (channel) {
      // Mark as initialized immediately to prevent duplicate callbacks
      if (qwebchannelInitialized) {
        log("QWebChannel callback invoked but already initialized, ignoring");
        return;
      }
      qwebchannelInitialized = true;
      qwebchannelInitializing = false;
      log("QWebChannel callback invoked");
      log("Channel:", channel);
      log("Channel.objects:", channel.objects);

      const objectKeys = Object.keys(channel.objects);
      log("Object.keys():", objectKeys);
      log("Object.keys() length:", objectKeys.length);

      log("Trying direct access to chartBridge...");
      log("channel.objects.chartBridge:", channel.objects.chartBridge);
      log("channel.objects['chartBridge']:", channel.objects["chartBridge"]);

      const bridge = channel.objects.chartBridge;
      log("bridge assigned:", bridge);

      if (!bridge) {
        const availableKeys = [];
        for (const key in channel.objects) {
          availableKeys.push(key);
          log("  - Property:", key, "=", channel.objects[key]);
        }
        ChartManager.showOverlay(
          "chartBridge no está registrado.\nObjetos disponibles: " +
            availableKeys.join(", ")
        );
        return;
      }

      log("chartBridge found! Type:", typeof bridge);
      log("bridge properties:", Object.keys(bridge));

      if (typeof bridge.ready === "function") {
        log("Calling bridge.ready()...");
        try {
          bridge.ready();
          log("bridge.ready() called successfully");
        } catch (err) {
          console.error("Error calling bridge.ready():", err);
        }
      } else {
        warn("bridge.ready is not a function, type:", typeof bridge.ready);
      }

      if (bridge.push) {
        log("bridge.push exists, type:", typeof bridge.push);
        if (typeof bridge.push.connect === "function") {
          bridge.push.connect(function (payload) {
            log("=== RECEIVED PUSH ===");
            log("Payload length:", payload.length);

            if (!ok) {
              warn("Chart not initialized, ignoring");
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

              log("Message type:", msg.type);
              log("Candles:", msg.candles ? msg.candles.length : 0);
              log(
                "Indicators:",
                msg.indicators ? Object.keys(msg.indicators) : []
              );
              log(
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

                // DEBUG: Log first and last candle to identify the data
                if (msg.candles.length > 0) {
                  console.log("JS CHART: Receiving data, first_candle:", JSON.stringify(msg.candles[0]), "last_candle:", JSON.stringify(msg.candles[msg.candles.length - 1]));
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
              } else if (msg.type === "realtime_update") {
                // Realtime price update for last candle
                if (typeof msg.price === 'number') {
                  ChartManager.updateRealtimePrice(msg.price, msg.marketStatus || "");
                } else {
                  warn("Invalid realtime_update message:", msg);
                }
              } else {
                warn("Unknown message type:", msg.type);
              }
            } catch (err) {
              console.error("Error processing push:", err);
            }
          });
          log("Connected to bridge.push signal");
        } else {
          console.error("bridge.push.connect is not a function");
        }
      } else {
        console.error("bridge.push does not exist");
      }
    });
  }, QWEBCHANNEL_INIT_DELAY_MS);
});
