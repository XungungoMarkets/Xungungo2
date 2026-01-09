(function (global) {
  function createChart(container, options) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    container.innerHTML = '';
    container.appendChild(canvas);

    const chart = {
      _series: [],
      _candleSeries: null,
      addCandlestickSeries: addCandlestickSeries,
      addLineSeries: addLineSeries,
      removeSeries: removeSeries,
      timeScale: function () {
        return { fitContent: function () {} };
      },
    };

    function resize() {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
      render();
    }

    window.addEventListener('resize', resize);
    resize();

    function addCandlestickSeries(seriesOptions) {
      const series = buildSeries('candle', seriesOptions || {});
      chart._candleSeries = series;
      chart._series.push(series);
      return series;
    }

    function addLineSeries(seriesOptions) {
      const series = buildSeries('line', seriesOptions || {});
      chart._series.push(series);
      return series;
    }

    function removeSeries(series) {
      chart._series = chart._series.filter(item => item !== series);
      if (chart._candleSeries === series) {
        chart._candleSeries = null;
      }
      render();
    }

    function buildSeries(type, seriesOptions) {
      return {
        type: type,
        options: seriesOptions,
        data: [],
        setData: function (data) {
          this.data = data || [];
          render();
        },
        applyOptions: function (nextOptions) {
          this.options = Object.assign({}, this.options, nextOptions);
          render();
        },
      };
    }

    function render() {
      if (!ctx) {
        return;
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = (options && options.layout && options.layout.background && options.layout.background.color) || '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const candleSeries = chart._candleSeries;
      const lineSeries = chart._series.filter(series => series.type === 'line');

      const allValues = [];
      if (candleSeries) {
        candleSeries.data.forEach(item => {
          allValues.push(item.high, item.low);
        });
      }
      lineSeries.forEach(series => {
        if (series.options.visible === false) {
          return;
        }
        series.data.forEach(item => {
          allValues.push(item.value);
        });
      });

      if (allValues.length === 0) {
        return;
      }

      const minValue = Math.min.apply(null, allValues);
      const maxValue = Math.max.apply(null, allValues);
      const padding = 20;
      const plotWidth = canvas.width - padding * 2;
      const plotHeight = canvas.height - padding * 2;

      function yScale(value) {
        if (maxValue === minValue) {
          return padding + plotHeight / 2;
        }
        return padding + (maxValue - value) / (maxValue - minValue) * plotHeight;
      }

      if (candleSeries && candleSeries.data.length > 0) {
        const data = candleSeries.data;
        const step = plotWidth / data.length;
        data.forEach((item, idx) => {
          const x = padding + idx * step + step / 2;
          const openY = yScale(item.open);
          const closeY = yScale(item.close);
          const highY = yScale(item.high);
          const lowY = yScale(item.low);
          const up = item.close >= item.open;
          const color = up ? (candleSeries.options.upColor || '#26a69a') : (candleSeries.options.downColor || '#ef5350');

          ctx.strokeStyle = color;
          ctx.beginPath();
          ctx.moveTo(x, highY);
          ctx.lineTo(x, lowY);
          ctx.stroke();

          ctx.fillStyle = color;
          const bodyHeight = Math.max(1, Math.abs(closeY - openY));
          const bodyY = Math.min(openY, closeY);
          ctx.fillRect(x - step * 0.3, bodyY, step * 0.6, bodyHeight);
        });
      }

      lineSeries.forEach(series => {
        if (series.options.visible === false || series.data.length === 0) {
          return;
        }
        ctx.strokeStyle = series.options.color || '#3366ff';
        ctx.lineWidth = series.options.lineWidth || 2;
        ctx.beginPath();
        const step = plotWidth / series.data.length;
        series.data.forEach((item, idx) => {
          const x = padding + idx * step + step / 2;
          const y = yScale(item.value);
          if (idx === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        });
        ctx.stroke();
      });
    }

    return chart;
  }

  global.LightweightCharts = { createChart: createChart };
})(window);
