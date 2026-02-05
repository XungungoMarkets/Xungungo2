// price-axis-label.js
// Renderer for price axis labels (e.g., extended hours labels)

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

export class PriceAxisLabelPrimitive {
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
