# Xungungo - Arquitectura del Sistema de Plugins

## 🎯 Visión General

Xungungo usa un sistema de plugins completamente modular donde:
1. **Python** define los indicadores y sus propiedades de renderizado
2. **JavaScript** renderiza automáticamente según las definiciones
3. **No hay acoplamiento** entre plugins y el core del sistema

## 🔄 Flujo de Datos

```
┌─────────────────────────────────────────────────────────┐
│  1. AUTODISCOVERY (al iniciar)                          │
│     indicators/*.py → PluginManager                     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  2. FETCH DATA                                          │
│     YFinance → OHLCV DataFrame                          │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  3. COMPUTE INDICATORS                                  │
│     Plugin.apply(df) → df + indicator columns           │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  4. BUILD PAYLOAD                                       │
│     {                                                   │
│       candles: [...],                                   │
│       indicators: {col: [{time, value}]},               │
│       seriesDefs: [                                     │
│         {id, column, type: "line"},                     │
│         {id, type: "fill_between", series1, series2},   │
│         {id, type: "band", upperColumn, lowerColumn}    │
│       ]                                                 │
│     }                                                   │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  5. SEND TO FRONTEND                                    │
│     Python → WebChannel → JavaScript                    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  6. RENDER                                              │
│     chart.js dispatches to:                             │
│     - LineSeries (type: "line")                         │
│     - AdvancedRenderer (type: "fill_between", "band")   │
└─────────────────────────────────────────────────────────┘
```

## 📁 Estructura de Archivos

```
xungungo/
├── indicators/              # Plugins Python
│   ├── __init__.py
│   ├── base.py             # IndicatorPlugin base class
│   ├── manager.py          # PluginManager con autodiscovery
│   ├── kalman.py           # Ejemplo: fill_between
│   ├── bollinger.py        # Ejemplo: band
│   ├── rsi.py              # Ejemplo: line
│   └── fibonacci.py        # Ejemplo: múltiples lines
│
├── controllers/
│   └── ticker_controller.py  # Coordina plugins + bridge
│
├── bridge/
│   └── chart_bridge.py       # Comunicación Qt <-> JS
│
└── ui/
    └── qml/
        ├── Main.qml
        ├── pages/
        │   └── TickerPage.qml
        └── components/
            └── AutocompleteField.qml

web/
├── index.html
├── chart.js                  # Core chart logic
└── advanced_renderer.js      # FillBetween + Band renderers
```

## 🔌 Anatomía de un Plugin

### Python Side

```python
from xungungo.indicators.base import IndicatorPlugin

class MiPlugin(IndicatorPlugin):
    # 1. Metadata
    id = "mi_plugin"
    name = "Mi Plugin"
    description = "Hace algo útil"
    
    # 2. Configuration
    def default_config(self) -> Dict[str, Any]:
        return {"period": 14}
    
    def config_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {...}}
    
    # 3. Computation
    def apply(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        # Agrega columnas al DataFrame
        df["mi_value"] = ...
        return df
    
    # 4. Rendering definition
    def chart_series(self) -> List[Dict[str, Any]]:
        return [
            {"id": "mi_value", "column": "mi_value", "type": "line"}
        ]
```

### JavaScript Side (automático)

El `chart.js` recibe las definiciones y renderiza automáticamente:

```javascript
// Para type: "line"
ensureLineSeries(id).setData(data)

// Para type: "fill_between"
advancedRenderer.apply(chart, seriesDefs, indicators)

// Para type: "band"
advancedRenderer.apply(chart, seriesDefs, indicators)
```

## 🎨 Tipos de Renderizado

### 1. Line (básico)
```python
{"id": "ma_20", "column": "ma_20", "type": "line", "pane": "main"}
```
→ Crea `LineSeries` con los datos de `ma_20`

### 2. Fill Between (dos líneas)
```python
{"id": "fast", "column": "fast", "type": "line"},
{"id": "slow", "column": "slow", "type": "line"},
{
    "id": "fill",
    "type": "fill_between",
    "series1": "fast",
    "series2": "slow",
    "upColor": "rgba(...)",
    "downColor": "rgba(...)"
}
```
→ Crea dos `LineSeries` + `FillBetweenPrimitive` que detecta cruces y colorea según dirección

### 3. Band (área entre bounds)
```python
{"id": "bb_middle", "column": "bb_middle", "type": "line"},
{
    "id": "bb_band",
    "type": "band",
    "upperColumn": "bb_upper",
    "lowerColumn": "bb_lower",
    "fillColor": "rgba(...)"
}
```
→ Crea `LineSeries` invisible + `BandPrimitive` que rellena entre upper y lower

## 🚀 Agregar un Nuevo Plugin

### Paso 1: Crear archivo
```bash
touch indicators/mi_indicador.py
```

### Paso 2: Implementar clase
```python
class MiIndicadorPlugin(IndicatorPlugin):
    id = "mi_indicador"
    # ... implementar métodos abstractos
```

### Paso 3: Reiniciar app
```bash
python -m xungungo.main
```

**¡Eso es todo!** El plugin aparece automáticamente en la UI.

## 🔧 Debugging

### Ver qué plugins se cargaron
```
🔍 Discovering plugins in: /path/to/indicators
  ✓ Registered plugin: kalman (Kalman)
  ✓ Registered plugin: bollinger (Bollinger Bands)
  ✓ Registered plugin: rsi (RSI)
  ✗ Failed to load module broken: SyntaxError
✓ Plugin discovery complete. Loaded 3 plugins.
```

### Ver payload enviado al frontend
```python
# En ticker_controller.py, línea 145
print(json.dumps(payload, indent=2))
```

### Ver logs del chart
Abre las DevTools del WebEngineView:
```javascript
console.log("=== RECEIVED PUSH ===")
console.log("Indicators:", Object.keys(msg.indicators))
console.log("Series defs:", msg.seriesDefs)
```

## 🎯 Ventajas del Sistema

### ✅ Para desarrolladores de plugins
- **Simple**: Solo Python, sin JS en el 90% de casos
- **Declarativo**: Defines QUÉ renderizar, no CÓMO
- **Type-safe**: TypedDict para series definitions
- **Testeable**: Plugins son funciones puras

### ✅ Para el core
- **Desacoplado**: Plugins no conocen el chart
- **Extensible**: Agregar nuevos tipos de render es fácil
- **Mantenible**: Cambios en plugins no afectan el core
- **Escalable**: 100 plugins no requieren cambios en el core

### ✅ Para usuarios
- **Plug & Play**: Agregar plugin = copiar archivo
- **No setup**: Autodiscovery automático
- **Predecible**: Comportamiento consistente entre plugins

## 🔮 Futuro

### Corto plazo
1. **Paneles separados**: `pane: "separate"` para osciladores
2. **Más tipos**: `histogram`, `area`, `baseline`
3. **UI dinámica**: Generar controles desde `config_schema`
4. **Hot reload**: Cambiar plugins sin reiniciar

### Largo plazo
1. **Plugin marketplace**: Compartir plugins entre usuarios
2. **Backtesting hooks**: Plugins que generan señales
3. **Alerts**: Sistema de notificaciones basado en plugins
4. **Multi-timeframe**: Indicadores en diferentes timeframes
5. **Custom primitives**: API para primitives JS desde Python

## 📚 Referencias

- [LightweightCharts v5 Docs](https://tradingview.github.io/lightweight-charts/)
- [Series Primitives API](https://tradingview.github.io/lightweight-charts/docs/plugins)
- [PySide6 WebChannel](https://doc.qt.io/qtforpython-6/PySide6/QtWebChannel/index.html)