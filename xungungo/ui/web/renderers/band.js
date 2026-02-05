// band.js
// Renderer for upper/lower bands (e.g., Bollinger Bands)

import { log, warn } from './utils.js';

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

export class BandPrimitive {
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
