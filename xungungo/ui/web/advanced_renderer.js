// advanced_renderer.js
// Sistema genérico de renderizado avanzado para LightweightCharts v5+
// Ahora modularizado - este archivo mantiene compatibilidad con código existente

import {
  AdvancedRenderer,
  PriceAxisLabelPrimitive,
  FibonacciLevelsPrimitive,
  FillBetweenPrimitive,
  BandPrimitive,
  HorizontalLinesPrimitive
} from './renderers/index.js';

// Export to global scope for backwards compatibility
window.AdvancedRenderer = AdvancedRenderer;
window.PriceAxisLabelPrimitive = PriceAxisLabelPrimitive;
window.FibonacciLevelsPrimitive = FibonacciLevelsPrimitive;
window.FillBetweenPrimitive = FillBetweenPrimitive;
window.BandPrimitive = BandPrimitive;
window.HorizontalLinesPrimitive = HorizontalLinesPrimitive;
