// advanced_renderer.js
// Sistema genérico de renderizado avanzado para LightweightCharts v5+
// Soporta: fill_between, bands, y otros patrones comunes

(function (global) {
  "use strict";

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
        console.warn("BandRenderer: not enabled");
        return;
      }

      if (!state.upperData || !state.lowerData) {
        console.warn("BandRenderer: missing data", {
          upper: !!state.upperData,
          lower: !!state.lowerData
        });
        return;
      }

      const upper = state.upperData;
      const lower = state.lowerData;

      if (upper.length < 2 || lower.length < 2) {
        console.warn(`BandRenderer: insufficient data - upper=${upper.length}, lower=${lower.length}`);
        return;
      }

      console.log(`BandRenderer: Drawing band with ${upper.length} points`);

      target.useMediaCoordinateSpace((scope) => {
        const ctx = scope.context;
        const chart = state.chart;
        const series = state.series;
        const referenceSeries = state.referenceSeries;

        if (!chart || !series) {
          console.warn("BandRenderer: missing chart or series");
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
          console.warn("BandRenderer: insufficient valid points after coordinate conversion");
          return;
        }

        console.log(`BandRenderer: Drawing with ${points.length} valid points, first point:`, points[0]);

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

        console.log("BandRenderer: Fill completed");
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
        }
        // Add more types here as needed
      }
    }

    _applyFillBetween(chart, ensureLineSeriesFn, def, indicators) {
      const id = def.id;
      const series1Id = def.series1;
      const series2Id = def.series2;

      // Get data by column name (series1/series2 are actually column names)
      const data1 = indicators[series1Id];
      const data2 = indicators[series2Id];

      if (!data1 || !data2) {
        console.warn(`FillBetween ${id}: Missing data for ${series1Id} or ${series2Id}`);
        return;
      }

      console.log(`FillBetween ${id}: Found data1=${data1.length} points, data2=${data2.length} points`);

      // Ensure line series exist (using series IDs which match column names)
      const series1 = ensureLineSeriesFn(series1Id);
      const series2 = ensureLineSeriesFn(series2Id);

      if (!series1 || !series2) {
        console.warn(`FillBetween ${id}: Missing series ${series1Id} or ${series2Id}`);
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
        console.log(`AdvancedRenderer: Recreating primitive ${id} (series changed)`);
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
          console.log(`AdvancedRenderer: FillBetween primitive created and attached (${id})`);
        } else {
          console.warn(`AdvancedRenderer: attachPrimitive not available`);
          return;
        }
      } else {
        console.log(`AdvancedRenderer: Reusing existing primitive ${id}`);
      }

      primitive.setEnabled(true);
      primitive.setSeriesRefs(series1, series2);
      primitive.setData(data1, data2);
    }

    _applyBand(chart, ensureLineSeriesFn, def, indicators, candleSeries) {
      const id = def.id;
      const upperCol = def.upperColumn;
      const lowerCol = def.lowerColumn;

      console.log(`Band ${id}: Looking for columns ${upperCol} and ${lowerCol}`);

      const upperData = indicators[upperCol];
      const lowerData = indicators[lowerCol];

      if (!upperData || !lowerData) {
        console.warn(`Band ${id}: Missing data - upper=${!!upperData}, lower=${!!lowerData}`);
        return;
      }

      console.log(`Band ${id}: Found upper=${upperData.length} points, lower=${lowerData.length} points`);

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

      console.log(`Band ${id}: Setting ${hostData.length} points on host series`);
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
          console.log(`AdvancedRenderer: Band primitive attached (${id})`);
        } else {
          console.warn(`AdvancedRenderer: attachPrimitive not available`);
          return;
        }
      }

      primitive.setEnabled(true);
      primitive.setData(upperData, lowerData);

      // CRITICAL FIX: Use candlestick series as reference for price coordinates
      if (candleSeries) {
        primitive.setReferenceSeries(candleSeries);
        console.log(`Band ${id}: Set reference series to candlestick`);
      } else {
        console.warn(`Band ${id}: No candleSeries available, using host series`);
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
      console.log(`AdvancedRenderer: Removed primitive ${id}`);
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
        console.log(`AdvancedRenderer: Removed ${toRemove.length} unused primitives:`, toRemove);
      }
    }

    /**
     * Clear all primitives
     */
    clear() {
      console.log(`AdvancedRenderer: Clearing all ${this._primitives.size} primitives`);
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
})(window);