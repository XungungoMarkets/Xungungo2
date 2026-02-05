// manager.js
// Advanced Renderer Manager - coordinates all rendering primitives

import { log, warn } from './utils.js';
import { FillBetweenPrimitive } from './fill-between.js';
import { BandPrimitive } from './band.js';
import { HorizontalLinesPrimitive } from './horizontal-lines.js';

export class AdvancedRenderer {
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
      } else if (type === "fibonacci_levels") {
        this._applyFibonacciLevels(chart, ensureLineSeriesFn, def, indicators, candleSeries);
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

  _applyFibonacciLevels(chart, ensureLineSeriesFn, def, indicators, candleSeries) {
    const id = def.id;
    const levelDefs = def.levels || [];

    if (levelDefs.length === 0) {
      warn(`FibonacciLevels ${id}: No levels provided`);
      return;
    }

    // Remove existing price lines for this fibonacci set
    if (!this._fibonacciPriceLines) {
      this._fibonacciPriceLines = new Map();
    }

    const existingData = this._fibonacciPriceLines.get(id);
    if (existingData && existingData.lines && existingData.series) {
      for (const line of existingData.lines) {
        try {
          existingData.series.removePriceLine(line);
        } catch (e) {
          // Line may already be removed
        }
      }
    }
    this._fibonacciPriceLines.delete(id);

    // Build levels with prices extracted from indicator data
    const priceLines = [];
    for (const levelDef of levelDefs) {
      const column = levelDef.column;
      const data = indicators[column];

      if (!data || data.length === 0) {
        warn(`FibonacciLevels ${id}: No data for column ${column}`);
        continue;
      }

      // Get price from first data point (Fibonacci levels are constant)
      const price = data[0].value;
      const color = levelDef.color || "#888888";
      const lineWidth = levelDef.lineWidth || 1;
      const lineStyle = levelDef.lineStyle || 0; // 0=solid, 2=dashed

      // Map lineStyle to LightweightCharts LineStyle enum
      let lwcLineStyle = 0; // Solid
      if (lineStyle === 2) {
        lwcLineStyle = 2; // Dashed
      }

      try {
        // Create native price line on the candle series
        // This shows the label in the price axis (right side), not over candles
        const priceLine = candleSeries.createPriceLine({
          price: price,
          color: color,
          lineWidth: lineWidth,
          lineStyle: lwcLineStyle,
          lineVisible: true,
          axisLabelVisible: true,  // Show label in price axis
          title: levelDef.label || "",  // Label shown at the line start
        });

        priceLines.push(priceLine);
      } catch (e) {
        warn(`FibonacciLevels ${id}: Error creating price line for ${levelDef.label}:`, e);
      }
    }

    // Store price lines and series reference for cleanup
    this._fibonacciPriceLines.set(id, { lines: priceLines, series: candleSeries });
    log(`FibonacciLevels ${id}: Created ${priceLines.length} price lines`);
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

    // Also remove fibonacci price lines if they exist
    this._removeFibonacciPriceLines(id);

    log(`AdvancedRenderer: Removed primitive ${id}`);
  }

  /**
   * Remove fibonacci price lines for a given id
   */
  _removeFibonacciPriceLines(id) {
    if (!this._fibonacciPriceLines) return;

    const lineData = this._fibonacciPriceLines.get(id);
    if (lineData) {
      const { lines, series } = lineData;
      if (lines && series) {
        for (const line of lines) {
          try {
            series.removePriceLine(line);
          } catch (e) {
            // Line may already be removed
          }
        }
      }
      this._fibonacciPriceLines.delete(id);
      log(`AdvancedRenderer: Removed ${lines ? lines.length : 0} fibonacci price lines for ${id}`);
    }
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

    // Also check fibonacci price lines
    if (this._fibonacciPriceLines) {
      for (const [id] of this._fibonacciPriceLines.entries()) {
        if (!currentIds.has(id) && !toRemove.includes(id)) {
          toRemove.push(id);
        }
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

    // Clear all fibonacci price lines
    if (this._fibonacciPriceLines) {
      for (const [id] of this._fibonacciPriceLines.entries()) {
        this._removeFibonacciPriceLines(id);
      }
      this._fibonacciPriceLines.clear();
    }
  }
}
