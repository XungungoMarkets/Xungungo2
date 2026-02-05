// fibonacci-levels.js
// Renderer for Fibonacci retracement/extension levels with labels

class FibonacciLevelsRenderer {
  constructor(getState) {
    this._getState = getState;
  }

  drawBackground(target) {
    const state = this._getState();
    if (!state.enabled || !state.levels || state.levels.length === 0) return;

    target.useMediaCoordinateSpace((scope) => {
      const ctx = scope.context;
      const chart = state.chart;
      const referenceSeries = state.referenceSeries;

      if (!chart || !referenceSeries) return;

      const timeScale = chart.timeScale();
      const visibleRange = timeScale.getVisibleLogicalRange();
      if (!visibleRange) return;

      // Get the visible time range for drawing lines
      const barsInfo = state.barsInfo;
      let startTime = null;
      let endTime = null;

      if (barsInfo && barsInfo.length >= 2) {
        startTime = barsInfo[0].time;
        endTime = barsInfo[barsInfo.length - 1].time;
      }

      if (!startTime || !endTime) return;

      const x1 = timeScale.timeToCoordinate(startTime);
      const x2 = timeScale.timeToCoordinate(endTime);

      if (x1 == null || x2 == null) return;

      const lineWidth = state.lineWidth || 1;
      const showLabels = state.showLabels !== false;
      const labelPosition = state.labelPosition || "right";
      const fontSize = state.fontSize || 11;

      ctx.save();
      ctx.font = `${fontSize}px sans-serif`;
      ctx.textBaseline = "middle";

      for (const level of state.levels) {
        const y = referenceSeries.priceToCoordinate(level.price);
        if (y == null) continue;

        const color = level.color || "rgba(255,255,255,0.8)";
        const lineStyle = level.lineStyle || 0; // 0=solid, 2=dashed

        // Draw horizontal line
        ctx.strokeStyle = color;
        ctx.lineWidth = level.lineWidth || lineWidth;

        if (lineStyle === 2) {
          ctx.setLineDash([5, 3]);
        } else {
          ctx.setLineDash([]);
        }

        ctx.beginPath();
        ctx.moveTo(x1, y);
        ctx.lineTo(x2, y);
        ctx.stroke();

        // Draw label
        if (showLabels && level.label) {
          const padding = 4;
          const textWidth = ctx.measureText(level.label).width;
          const boxWidth = textWidth + padding * 2;
          const boxHeight = fontSize + padding * 2;

          let labelX;
          if (labelPosition === "left") {
            labelX = x1 + 5;
          } else {
            // right - position near price axis
            labelX = x2 - boxWidth - 5;
          }

          // Draw label background with transparency
          ctx.fillStyle = color;
          ctx.globalAlpha = 0.85;
          ctx.fillRect(labelX, y - boxHeight / 2, boxWidth, boxHeight);
          ctx.globalAlpha = 1.0;

          // Draw label text
          ctx.fillStyle = level.textColor || "#FFFFFF";
          ctx.textAlign = "left";
          ctx.fillText(level.label, labelX + padding, y);
        }
      }

      ctx.restore();
    });
  }

  draw() {}
}

class FibonacciLevelsPaneView {
  constructor(getState) {
    this._renderer = new FibonacciLevelsRenderer(getState);
  }
  renderer() {
    return this._renderer;
  }
  zOrder() {
    return "top";
  }
}

export class FibonacciLevelsPrimitive {
  constructor(options) {
    this._opts = options || {};
    this._enabled = true;
    this._chart = null;
    this._series = null;
    this._referenceSeries = null;
    this._requestUpdate = null;
    this._levels = [];
    this._barsInfo = [];
    this._paneView = new FibonacciLevelsPaneView(() => this._state());
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

  setBarsInfo(barsInfo) {
    this._barsInfo = barsInfo || [];
    this._safeRequestUpdate();
  }

  setLevels(levels) {
    this._levels = levels || [];
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
      levels: this._levels,
      barsInfo: this._barsInfo,
      lineWidth: this._opts.lineWidth || 1,
      showLabels: this._opts.showLabels !== false,
      labelPosition: this._opts.labelPosition || "right",
      fontSize: this._opts.fontSize || 11,
    };
  }
}
