// advanced_renderer.js
// Sistema genérico de renderizado avanzado para LightweightCharts v5+
// Soporta: fill_between, bands, y otros patrones comunes

(function (global) {
  "use strict";

  const DEBUG = global.XUNGUNGO_DEBUG === true;
  const log = (...args) => {
    if (DEBUG) console["log"](...args);
  };
  const warn = (...args) => {
    if (DEBUG) console["warn"](...args);
  };

  // ========================================
  // FillBetween Renderer
  // ========================================
  class FillBetweenRenderer {
    constructor(getState) {
      this._getState = getState;
    }

    drawBackground(target) {
      const state = this._getState();
      if (!state.enabled || !state.series1 || !state.series2) return;

      const data1 = state.data1;
      const data2 = state.data2;
      if (!data1 || !data2 || data1.length < 2 || data2.length < 2) return;

      target.useMediaCoordinateSpace((scope) => {
        const ctx = scope.context;
        const chart = state.chart;
        const series1 = state.series1;
        const series2 = state.series2;

        if (!chart || !series1 || !series2) return;

        const timeScale = chart.timeScale();

        // Map time -> series2 value
        const data2Map = new Map();
        for (const p of data2) data2Map.set(p.time, p.value);

        let currentSegment = null; // { isAbove: bool, points: [{x, y1, y2}] }

        const upColor = state.upColor || "rgba(38,166,154,0.2)";
        const downColor = state.downColor || "rgba(239,83,80,0.2)";

        const flush = () => {
          if (!currentSegment || currentSegment.points.length < 2) return;

          ctx.save();
          ctx.fillStyle = currentSegment.isAbove ? upColor : downColor;
          ctx.beginPath();

          // Top edge (series1)
          for (let i = 0; i < currentSegment.points.length; i++) {
            const p = currentSegment.points[i];
            if (i === 0) ctx.moveTo(p.x, p.y1);
            else ctx.lineTo(p.x, p.y1);
          }

          // Bottom edge (series2, reversed)
          for (let i = currentSegment.points.length - 1; i >= 0; i--) {
            const p = currentSegment.points[i];
            ctx.lineTo(p.x, p.y2);
          }

          ctx.closePath();
          ctx.fill();
          ctx.restore();
        };

        for (const p1 of data1) {
          const v2 = data2Map.get(p1.time);
          if (v2 == null) continue;

          const isAbove = p1.value >= v2;

          const x = timeScale.timeToCoordinate(p1.time);
          const y1 = series1.priceToCoordinate(p1.value);
          const y2 = series2.priceToCoordinate(v2);

          if (x == null || y1 == null || y2 == null) continue;

          if (!currentSegment) {
            currentSegment = { isAbove, points: [{ x, y1, y2 }] };
            continue;
          }

          if (currentSegment.isAbove !== isAbove) {
            flush();
            currentSegment = { isAbove, points: [{ x, y1, y2 }] };
          } else {
            currentSegment.points.push({ x, y1, y2 });
          }
        }

        flush();
      });
    }

    draw() {}
  }

  class FillBetweenPaneView {
    constructor(getState) {
      this._renderer = new FillBetweenRenderer(getState);
    }
    renderer() {
      return this._renderer;
    }
    zOrder() {
      return undefined;
    }
  }

  class FillBetweenPrimitive {
    constructor(options) {
      this._opts = options || {};
      this._enabled = true;
      this._chart = null;
      this._series = null;
      this._requestUpdate = null;
      this._series1 = null;
      this._series2 = null;
      this._data1 = [];
      this._data2 = [];
      this._paneView = new FillBetweenPaneView(() => this._state());
    }

    attached(params) {
      this._chart = params.chart;
      this._series = params.series;
      this._requestUpdate = params.requestUpdate;
    }

    detached() {
      this._chart = null;
      this._series = null;
      this._requestUpdate = null;
    }

    paneViews() {
      return [this._paneView];
    }

    updateAllViews() {}

    setEnabled(enabled) {
      this._enabled = !!enabled;
      this._safeRequestUpdate();
    }

    setSeriesRefs(series1, series2) {
      this._series1 = series1;
      this._series2 = series2;
      this._safeRequestUpdate();
    }

    setData(data1, data2) {
      this._data1 = data1 || [];
      this._data2 = data2 || [];
      this._safeRequestUpdate();
    }

    _safeRequestUpdate() {
      if (typeof this._requestUpdate === "function") {
        this._requestUpdate();
      }
    }

    _state() {
      return {
        enabled: this._enabled,
        chart: this._chart,
        series: this._series,
        series1: this._series1,
        series2: this._series2,
        data1: this._data1,
        data2: this._data2,
        upColor: this._opts.upColor || "rgba(38,166,154,0.2)",
        downColor: this._opts.downColor || "rgba(239,83,80,0.2)",
      };
    }
  }

  // ========================================
  // Band Renderer (upper/lower bounds)
  // ========================================
  class BandRenderer {
    constructor(getState) {
      this._getState = getState;
    }

    drawBackground(target) {
      const state = this._getState();

      if (!state.enabled) {
        warn("BandRenderer: not enabled");
        return;
      }

      if (!state.upperData || !state.lowerData) {
        warn("BandRenderer: missing data", {
          upper: !!state.upperData,
          lower: !!state.lowerData
        });
        return;
      }

      const upper = state.upperData;
      const lower = state.lowerData;

      if (upper.length < 2 || lower.length < 2) {
        warn(`BandRenderer: insufficient data - upper=${upper.length}, lower=${lower.length}`);
        return;
      }

      log(`BandRenderer: Drawing band with ${upper.length} points`);

      target.useMediaCoordinateSpace((scope) => {
        const ctx = scope.context;
        const chart = state.chart;
        const series = state.series;
        const referenceSeries = state.referenceSeries;

        if (!chart || !series) {
          warn("BandRenderer: missing chart or series");
          return;
        }

        // Use reference series (candlestick) for price scale if available, otherwise use host series
        const priceScale = referenceSeries || series;

        const timeScale = chart.timeScale();
        const fillColor = state.fillColor || "rgba(33,150,243,0.1)";

        // Map time -> lower value
        const lowerMap = new Map();
        for (const p of lower) lowerMap.set(p.time, p.value);

        const points = [];

        for (const u of upper) {
          const l = lowerMap.get(u.time);
          if (l == null) continue;

          const x = timeScale.timeToCoordinate(u.time);
          const yUpper = priceScale.priceToCoordinate(u.value);
          const yLower = priceScale.priceToCoordinate(l);

          if (x == null || yUpper == null || yLower == null) continue;

          points.push({ x, yUpper, yLower });
        }

        if (points.length < 2) {
          warn("BandRenderer: insufficient valid points after coordinate conversion");
          return;
        }

        log(`BandRenderer: Drawing with ${points.length} valid points, first point:`, points[0]);

        ctx.save();
        ctx.fillStyle = fillColor;
        ctx.beginPath();

        // Draw upper edge
        for (let i = 0; i < points.length; i++) {
          const p = points[i];
          if (i === 0) ctx.moveTo(p.x, p.yUpper);
          else ctx.lineTo(p.x, p.yUpper);
        }

        // Draw lower edge (reversed)
        for (let i = points.length - 1; i >= 0; i--) {
          const p = points[i];
          ctx.lineTo(p.x, p.yLower);
        }

        ctx.closePath();
        ctx.fill();
        ctx.restore();

        log("BandRenderer: Fill completed");
      });
    }

    draw() {}
  }

  class BandPaneView {
    constructor(getState) {
      this._renderer = new BandRenderer(getState);
    }
    renderer() {
      return this._renderer;
    }
    zOrder() {
      return undefined;
    }
  }

  class BandPrimitive {
    constructor(options) {
      this._opts = options || {};
      this._enabled = true;
      this._chart = null;
      this._series = null;
      this._referenceSeries = null;
      this._requestUpdate = null;
      this._upperData = [];
      this._lowerData = [];
      this._paneView = new BandPaneView(() => this._state());
    }

    attached(params) {
      this._chart = params.chart;
      this._series = params.series;
      this._requestUpdate = params.requestUpdate;
    }

    detached() {
      this._chart = null;
      this._series = null;
      this._requestUpdate = null;
    }

    paneViews() {
      return [this._paneView];
    }

    updateAllViews() {}

    setEnabled(enabled) {
      this._enabled = !!enabled;
      this._safeRequestUpdate();
    }

    setData(upperData, lowerData) {
      this._upperData = upperData || [];
      this._lowerData = lowerData || [];
      this._safeRequestUpdate();
    }

    _safeRequestUpdate() {
      if (typeof this._requestUpdate === "function") {
        this._requestUpdate();
      }
    }

    _state() {
      return {
        enabled: this._enabled,
        chart: this._chart,
        series: this._series,
        referenceSeries: this._referenceSeries,
        upperData: this._upperData,
        lowerData: this._lowerData,
        fillColor: this._opts.fillColor || "rgba(33,150,243,0.1)",
      };
    }

    setReferenceSeries(referenceSeries) {
      this._referenceSeries = referenceSeries;
      this._safeRequestUpdate();
    }
  }

  // ========================================
  // Horizontal Lines Renderer (for TDST levels)
  // ========================================
  class HorizontalLinesRenderer {
    constructor(getState) {
      this._getState = getState;
    }

    drawBackground(target) {
      const state = this._getState();
      if (!state.enabled || !state.segments || state.segments.length === 0) return;

      target.useMediaCoordinateSpace((scope) => {
        const ctx = scope.context;
        const chart = state.chart;
        const referenceSeries = state.referenceSeries;

        if (!chart || !referenceSeries) return;

        const timeScale = chart.timeScale();
        const color = state.color || "rgba(255,255,255,0.8)";
        const lineWidth = state.lineWidth || 2;

        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;

        for (const seg of state.segments) {
          const x1 = timeScale.timeToCoordinate(seg.startTime);
          const x2 = timeScale.timeToCoordinate(seg.endTime);
          const y = referenceSeries.priceToCoordinate(seg.value);

          if (x1 == null || x2 == null || y == null) continue;

          ctx.beginPath();
          ctx.moveTo(x1, y);
          ctx.lineTo(x2, y);
          ctx.stroke();
        }

        ctx.restore();
      });
    }

    draw() {}
  }

  class HorizontalLinesPaneView {
    constructor(getState) {
      this._renderer = new HorizontalLinesRenderer(getState);
    }
    renderer() {
      return this._renderer;
    }
    zOrder() {
      return undefined;
    }
  }

  class HorizontalLinesPrimitive {
    constructor(options) {
      this._opts = options || {};
      this._enabled = true;
      this._chart = null;
      this._series = null;
      this._referenceSeries = null;
      this._requestUpdate = null;
      this._segments = [];
      this._paneView = new HorizontalLinesPaneView(() => this._state());
    }

    attached(params) {
      this._chart = params.chart;
      this._series = params.series;
      this._requestUpdate = params.requestUpdate;
    }

    detached() {
      this._chart = null;
      this._series = null;
      this._requestUpdate = null;
    }

    paneViews() {
      return [this._paneView];
    }

    updateAllViews() {}

    setEnabled(enabled) {
      this._enabled = !!enabled;
      this._safeRequestUpdate();
    }

    setReferenceSeries(referenceSeries) {
      this._referenceSeries = referenceSeries;
      this._safeRequestUpdate();
    }

    setSegments(segments) {
      this._segments = segments || [];
      this._safeRequestUpdate();
    }

    _safeRequestUpdate() {
      if (typeof this._requestUpdate === "function") {
        this._requestUpdate();
      }
    }

    _state() {
      return {
        enabled: this._enabled,
        chart: this._chart,
        series: this._series,
        referenceSeries: this._referenceSeries,
        segments: this._segments,
        color: this._opts.color || "rgba(255,255,255,0.8)",
        lineWidth: this._opts.lineWidth || 2,
      };
    }
  }

  // ========================================
  // Price Axis Label Primitive (for extended hours labels)
  // ========================================
  class PriceAxisLabelRenderer {
    constructor(getState) {
      this._getState = getState;
    }

    draw(target) {
      const state = this._getState();
      if (!state.enabled || state.price == null) return;

      target.useMediaCoordinateSpace((scope) => {
        const ctx = scope.context;
        const { text, price, bgColor, textColor } = state;

        // Get the y coordinate for the price
        const series = state.series;
        if (!series) return;

        const y = series.priceToCoordinate(price);
        if (y == null) return;

        // Draw the label box
        const padding = 4;
        const fontSize = 11;
        ctx.font = `${fontSize}px sans-serif`;
        const textWidth = ctx.measureText(text).width;
        const boxWidth = textWidth + padding * 2;
        const boxHeight = fontSize + padding * 2;

        // Position at the right edge of the price axis area
        const x = scope.mediaSize.width - boxWidth - 2;

        // Draw background
        ctx.fillStyle = bgColor || "#2962FF";
        ctx.fillRect(x, y - boxHeight / 2, boxWidth, boxHeight);

        // Draw text
        ctx.fillStyle = textColor || "#FFFFFF";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText(text, x + padding, y);
      });
    }
  }

  class PriceAxisLabelPaneView {
    constructor(getState) {
      this._renderer = new PriceAxisLabelRenderer(getState);
    }
    renderer() {
      return this._renderer;
    }
    zOrder() {
      return "top";
    }
  }

  class PriceAxisLabelPrimitive {
    constructor(options) {
      this._opts = options || {};
      this._enabled = false;
      this._chart = null;
      this._series = null;
      this._requestUpdate = null;
      this._price = null;
      this._text = "";
      this._paneView = new PriceAxisLabelPaneView(() => this._state());
    }

    attached(params) {
      this._chart = params.chart;
      this._series = params.series;
      this._requestUpdate = params.requestUpdate;
    }

    detached() {
      this._chart = null;
      this._series = null;
      this._requestUpdate = null;
    }

    paneViews() {
      return [this._paneView];
    }

    updateAllViews() {}

    setEnabled(enabled) {
      this._enabled = !!enabled;
      this._safeRequestUpdate();
    }

    setPrice(price) {
      this._price = price;
      this._safeRequestUpdate();
    }

    setText(text) {
      this._text = text;
      this._safeRequestUpdate();
    }

    setColors(bgColor, textColor) {
      this._opts.bgColor = bgColor;
      this._opts.textColor = textColor;
      this._safeRequestUpdate();
    }

    _safeRequestUpdate() {
      if (typeof this._requestUpdate === "function") {
        this._requestUpdate();
      }
    }

    _state() {
      return {
        enabled: this._enabled,
        chart: this._chart,
        series: this._series,
        price: this._price,
        text: this._text,
        bgColor: this._opts.bgColor || "#2962FF",
        textColor: this._opts.textColor || "#FFFFFF",
      };
    }
  }

  // ========================================
  // Advanced Renderer Manager
  // ========================================
  class AdvancedRenderer {
    constructor() {
      this._primitives = new Map(); // id -> primitive instance
      this._seriesRefs = new Map(); // series id -> LineSeries instance
    }

    /**
     * Apply advanced rendering based on series definitions
     */
    apply(chart, ensureLineSeriesFn, seriesDefs, indicators, candleSeries) {
      if (!seriesDefs || !indicators) return;

      for (const def of seriesDefs) {
        const type = def.type;

        if (type === "fill_between") {
          this._applyFillBetween(chart, ensureLineSeriesFn, def, indicators);
        } else if (type === "band") {
          this._applyBand(chart, ensureLineSeriesFn, def, indicators, candleSeries);
        } else if (type === "horizontal_lines") {
          this._applyHorizontalLines(chart, ensureLineSeriesFn, def, indicators, candleSeries);
        }
        // Add more types here as needed
      }
    }

    _applyHorizontalLines(chart, ensureLineSeriesFn, def, indicators, candleSeries) {
      const id = def.id;
      const column = def.column;

      const data = indicators[column];
      if (!data || data.length === 0) {
        warn(`HorizontalLines ${id}: No data for column ${column}`);
        return;
      }

      // Convert data points into horizontal segments
      // Each segment is a continuous run of the same value
      const segments = [];
      let currentValue = null;
      let startTime = null;

      for (let i = 0; i < data.length; i++) {
        const point = data[i];

        if (currentValue === null) {
          // Start new segment
          currentValue = point.value;
          startTime = point.time;
        } else if (point.value !== currentValue) {
          // End current segment and start new one
          segments.push({
            value: currentValue,
            startTime: startTime,
            endTime: data[i - 1].time,
          });
          currentValue = point.value;
          startTime = point.time;
        }
      }

      // Close last segment
      if (currentValue !== null && startTime !== null) {
        segments.push({
          value: currentValue,
          startTime: startTime,
          endTime: data[data.length - 1].time,
        });
      }

      log(`HorizontalLines ${id}: Created ${segments.length} segments from ${data.length} points`);

      // Create a dummy host series
      const hostSeriesId = `${id}_host`;
      const hostSeries = ensureLineSeriesFn(hostSeriesId);

      if (!hostSeries) return;

      // Make host series invisible
      hostSeries.applyOptions({
        lineWidth: 0,
        priceLineVisible: false,
        lastValueVisible: false,
        visible: false,
      });

      // Set minimal data on host series
      hostSeries.setData(data.slice(0, 1));

      // Get or create primitive
      let primitive = this._primitives.get(id);

      const needsRecreate = primitive && (
        primitive._series !== hostSeries ||
        !primitive._series
      );

      if (needsRecreate) {
        log(`AdvancedRenderer: Recreating HorizontalLines primitive ${id} (series changed)`);
        this.remove(id);
        primitive = null;
      }

      if (!primitive) {
        primitive = new HorizontalLinesPrimitive({
          color: def.color || "rgba(255,255,255,0.8)",
          lineWidth: def.lineWidth || 2,
        });

        if (typeof hostSeries.attachPrimitive === "function") {
          hostSeries.attachPrimitive(primitive);
          this._primitives.set(id, primitive);
          log(`AdvancedRenderer: HorizontalLines primitive attached (${id})`);
        } else {
          warn(`AdvancedRenderer: attachPrimitive not available`);
          return;
        }
      }

      primitive.setEnabled(true);
      primitive.setReferenceSeries(candleSeries);
      primitive.setSegments(segments);
    }

    _applyFillBetween(chart, ensureLineSeriesFn, def, indicators) {
      const id = def.id;
      const series1Id = def.series1;
      const series2Id = def.series2;

      // Get data by column name (series1/series2 are actually column names)
      const data1 = indicators[series1Id];
      const data2 = indicators[series2Id];

      if (!data1 || !data2) {
        warn(`FillBetween ${id}: Missing data for ${series1Id} or ${series2Id}`);
        return;
      }

      log(`FillBetween ${id}: Found data1=${data1.length} points, data2=${data2.length} points`);

      // Ensure line series exist (using series IDs which match column names)
      const series1 = ensureLineSeriesFn(series1Id);
      const series2 = ensureLineSeriesFn(series2Id);

      if (!series1 || !series2) {
        warn(`FillBetween ${id}: Missing series ${series1Id} or ${series2Id}`);
        return;
      }

      // Get or create primitive
      let primitive = this._primitives.get(id);

      // Check if primitive exists but is attached to different series (series were recreated)
      const needsRecreate = primitive && (
        primitive._series1 !== series1 ||
        primitive._series2 !== series2 ||
        !primitive._series  // Host series was deleted
      );

      if (needsRecreate) {
        log(`AdvancedRenderer: Recreating primitive ${id} (series changed)`);
        this.remove(id);
        primitive = null;
      }

      if (!primitive) {
        primitive = new FillBetweenPrimitive({
          upColor: def.upColor || "rgba(38,166,154,0.2)",
          downColor: def.downColor || "rgba(239,83,80,0.2)",
        });

        // Attach to series1 (host)
        if (typeof series1.attachPrimitive === "function") {
          series1.attachPrimitive(primitive);
          this._primitives.set(id, primitive);
          log(`AdvancedRenderer: FillBetween primitive created and attached (${id})`);
        } else {
          warn(`AdvancedRenderer: attachPrimitive not available`);
          return;
        }
      } else {
        log(`AdvancedRenderer: Reusing existing primitive ${id}`);
      }

      primitive.setEnabled(true);
      primitive.setSeriesRefs(series1, series2);
      primitive.setData(data1, data2);
    }

    _applyBand(chart, ensureLineSeriesFn, def, indicators, candleSeries) {
      const id = def.id;
      const upperCol = def.upperColumn;
      const lowerCol = def.lowerColumn;

      log(`Band ${id}: Looking for columns ${upperCol} and ${lowerCol}`);

      const upperData = indicators[upperCol];
      const lowerData = indicators[lowerCol];

      if (!upperData || !lowerData) {
        warn(`Band ${id}: Missing data - upper=${!!upperData}, lower=${!!lowerData}`);
        return;
      }

      log(`Band ${id}: Found upper=${upperData.length} points, lower=${lowerData.length} points`);

      // Create a dummy series to host the primitive (or use existing)
      const hostSeriesId = `${id}_host`;
      const hostSeries = ensureLineSeriesFn(hostSeriesId);

      if (!hostSeries) return;

      // Make host series invisible
      hostSeries.applyOptions({
        lineWidth: 0,
        priceLineVisible: false,
        lastValueVisible: false,
      });

      // CRITICAL FIX: Set data on host series to make primitive render
      // Use the middle value between upper and lower as dummy data
      const hostData = upperData.map((u, i) => {
        const l = lowerData[i];
        if (!l || u.time !== l.time) return null;
        return {
          time: u.time,
          value: (u.value + l.value) / 2
        };
      }).filter(p => p !== null);

      log(`Band ${id}: Setting ${hostData.length} points on host series`);
      hostSeries.setData(hostData);

      // Get or create primitive
      let primitive = this._primitives.get(id);

      if (!primitive) {
        primitive = new BandPrimitive({
          fillColor: def.fillColor || "rgba(33,150,243,0.1)",
        });

        if (typeof hostSeries.attachPrimitive === "function") {
          hostSeries.attachPrimitive(primitive);
          this._primitives.set(id, primitive);
          log(`AdvancedRenderer: Band primitive attached (${id})`);
        } else {
          warn(`AdvancedRenderer: attachPrimitive not available`);
          return;
        }
      }

      primitive.setEnabled(true);
      primitive.setData(upperData, lowerData);

      // CRITICAL FIX: Use candlestick series as reference for price coordinates
      if (candleSeries) {
        primitive.setReferenceSeries(candleSeries);
        log(`Band ${id}: Set reference series to candlestick`);
      } else {
        warn(`Band ${id}: No candleSeries available, using host series`);
      }
    }

    /**
     * Remove a primitive
     */
    remove(id) {
      const primitive = this._primitives.get(id);
      if (primitive && primitive._series) {
        // Detach primitive
        if (typeof primitive._series.detachPrimitive === "function") {
          primitive._series.detachPrimitive(primitive);
        }
      }
      this._primitives.delete(id);
      log(`AdvancedRenderer: Removed primitive ${id}`);
    }

    /**
     * Remove primitives that are not in the provided set of IDs
     */
    removeUnused(currentIds) {
      const toRemove = [];
      for (const [id] of this._primitives.entries()) {
        if (!currentIds.has(id)) {
          toRemove.push(id);
        }
      }

      for (const id of toRemove) {
        this.remove(id);
      }

      if (toRemove.length > 0) {
        log(`AdvancedRenderer: Removed ${toRemove.length} unused primitives:`, toRemove);
      }
    }

    /**
     * Clear all primitives
     */
    clear() {
      log(`AdvancedRenderer: Clearing all ${this._primitives.size} primitives`);
      for (const [id, primitive] of this._primitives.entries()) {
        if (primitive._series && typeof primitive._series.detachPrimitive === "function") {
          primitive._series.detachPrimitive(primitive);
        }
      }
      this._primitives.clear();
    }
  }

  // Export to global scope
  global.AdvancedRenderer = AdvancedRenderer;
  global.PriceAxisLabelPrimitive = PriceAxisLabelPrimitive;
})(window);
