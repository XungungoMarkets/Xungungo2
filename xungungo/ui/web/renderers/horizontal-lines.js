// horizontal-lines.js
// Renderer for horizontal lines segments (e.g., TDST levels)

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

export class HorizontalLinesPrimitive {
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
