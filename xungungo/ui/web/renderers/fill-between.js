// fill-between.js
// Renderer for filling the area between two series

import { log } from './utils.js';

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

export class FillBetweenPrimitive {
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
