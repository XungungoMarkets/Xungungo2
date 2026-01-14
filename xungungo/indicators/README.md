# Plugin System - Xungungo

## 🎯 Autodiscovery

El sistema de plugins utiliza **autodiscovery** automático. Simplemente agrega un archivo `.py` a la carpeta `indicators/` y se cargará automáticamente al iniciar la aplicación.

## 📝 Cómo crear un plugin

### 1. Estructura básica

Crea un nuevo archivo en `indicators/`, por ejemplo `mi_indicador.py`:

```python
from __future__ import annotations
import pandas as pd
from typing import Dict, Any, List
from .base import IndicatorPlugin

class MiIndicadorPlugin(IndicatorPlugin):
    # Identificador único (usado internamente)
    id = "mi_indicador"
    
    # Nombre visible en la UI
    name = "Mi Indicador"
    
    # Descripción breve
    description = "Descripción de lo que hace este indicador"

    def default_config(self) -> Dict[str, Any]:
        """Configuración por defecto del plugin."""
        return {
            "param1": 14,
            "param2": "close",
        }

    def config_schema(self) -> Dict[str, Any]:
        """Schema JSON para validación y UI (futuro)."""
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "integer",
                    "minimum": 1,
                    "title": "Parámetro 1"
                },
                "param2": {
                    "type": "string",
                    "enum": ["close", "open", "high", "low"],
                    "title": "Fuente"
                },
            }
        }

    def apply(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Aplica el indicador al DataFrame.
        
        Args:
            df: DataFrame con columnas: timestamp, open, high, low, close, volume
            config: Configuración del usuario (o default_config si no hay override)
        
        Returns:
            DataFrame con columnas adicionales para el indicador
        """
        if df is None or df.empty:
            return df
        
        # Tu lógica aquí
        df = df.copy()
        
        # Ejemplo: agregar una columna
        df["mi_indicador_value"] = df["close"] * 1.1
        
        return df

    def chart_series(self) -> List[Dict[str, Any]]:
        """
        Define qué series se deben renderizar en el gráfico.
        
        Returns:
            Lista de dicts con:
            - id: identificador único de la serie
            - column: nombre de la columna en el DataFrame
            - type: "line" | "histogram" | "candlestick" (futuro)
            - pane: "main" | "separate" (futuro: paneles separados)
        """
        return [
            {
                "id": "mi_indicador_value",
                "column": "mi_indicador_value",
                "type": "line",
                "pane": "main",
            }
        ]
```

### 2. Ejemplos de plugins

#### Plugin simple (una línea)
Ver: `rsi.py` - Calcula RSI con niveles de sobrecompra/sobreventa

#### Plugin con múltiples series
Ver: `kalman.py` - Dos filtros Kalman (fast/slow)

#### Plugin con JavaScript personalizado
Ver: `kalman.py` + `kalman_plugin.js` - Renderizado de fill entre dos líneas

#### Plugin con cálculos complejos
Ver: `fibonacci.py` - Niveles de Fibonacci con detección automática de swing

## 🔄 Agregar/Quitar plugins

### ✅ Agregar un nuevo plugin
1. Crea `mi_plugin.py` en `indicators/`
2. Define tu clase heredando de `IndicatorPlugin`
3. Reinicia la aplicación
4. El plugin aparecerá automáticamente en la lista

### ❌ Quitar un plugin
1. Elimina el archivo `.py` de `indicators/`
2. Reinicia la aplicación
3. El plugin ya no estará disponible

### 🔁 Durante desarrollo
Si modificas un plugin, puedes llamar:
```python
plugin_manager.reload_plugins()
```

Esto preservará las configuraciones pero recargará el código.

## 🎨 JavaScript custom (OBSOLETO - Ya no necesario)

**¡Buenas noticias!** Ya no necesitas escribir JavaScript custom para la mayoría de casos de uso.

### Sistema anterior (obsoleto)
Antes tenías que crear archivos `.js` personalizados para cada plugin con renderizado especial.

### Sistema actual (recomendado)
Usa los tipos de renderizado integrados en `chart_series()`:

- **`fill_between`**: Fill entre dos líneas (ejemplo: Kalman fast/slow)
- **`band`**: Fill entre upper/lower bounds (ejemplo: Bollinger Bands)

Estos patrones cubren el 90% de los casos de uso y no requieren JavaScript.

### ¿Cuándo SÍ necesitas JavaScript custom?
Solo para casos muy avanzados como:
- Renderizados 3D o WebGL
- Animaciones complejas
- Formas geométricas custom
- Interactividad avanzada con el mouse

Para estos casos, puedes implementar el método opcional:
```python
def javascript_code(self) -> str | None:
    return """
    // Tu código JavaScript aquí
    // Será inyectado automáticamente en la página
    """
```

## 📊 Tipos de series soportadas

### Líneas básicas
```python
{
    "id": "ma_20",
    "column": "ma_20",
    "type": "line",
    "pane": "main"
}
```

### Fill Between (dos líneas)
```python
# Primero define las líneas
{"id": "fast", "column": "fast", "type": "line", "pane": "main"},
{"id": "slow", "column": "slow", "type": "line", "pane": "main"},

# Luego el fill
{
    "id": "fill",
    "type": "fill_between",
    "series1": "fast",
    "series2": "slow",
    "upColor": "rgba(38,166,154,0.2)",   # Cuando fast > slow
    "downColor": "rgba(239,83,80,0.2)",   # Cuando fast < slow
    "pane": "main"
}
```

### Band (área entre upper/lower)
```python
# Opcionalmente la línea del medio
{"id": "bb_middle", "column": "bb_middle", "type": "line", "pane": "main"},

# El band fill
{
    "id": "bb_band",
    "type": "band",
    "upperColumn": "bb_upper",
    "lowerColumn": "bb_lower",
    "fillColor": "rgba(33,150,243,0.15)",
    "pane": "main"
}
```

### Futuro
- `histogram`: Barras (HistogramSeries)
- `area`: Área bajo la curva (AreaSeries)
- `baseline`: Línea base con fill (BaselineSeries)
- `candlestick`: Velas (CandlestickSeries)
- `pane: "separate"`: Renderizar en panel propio (útil para RSI, MACD, etc.)

## 🧪 Testing de plugins

```python
# test_mi_plugin.py
import pandas as pd
from xungungo.indicators.mi_plugin import MiIndicadorPlugin

def test_basic():
    plugin = MiIndicadorPlugin()
    
    # DataFrame de prueba
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=100, freq="1h"),
        "open": range(100),
        "high": range(100),
        "low": range(100),
        "close": range(100),
        "volume": [1000] * 100,
    })
    
    config = plugin.default_config()
    result = plugin.apply(df, config)
    
    assert "mi_indicador_value" in result.columns
    assert len(result) == len(df)
```

## 🐛 Debugging

El manager imprime logs durante el discovery:

```
🔍 Discovering plugins in: /path/to/indicators
  ✓ Registered plugin: kalman (Kalman)
  ✓ Registered plugin: fibonacci (Fibonacci)
  ✓ Registered plugin: rsi (RSI)
  ✗ Failed to load module broken_plugin: SyntaxError
✓ Plugin discovery complete. Loaded 3 plugins.
```

## 🚀 Mejoras futuras

1. **Hot reload**: Recargar plugins sin reiniciar la app
2. **Plugin marketplace**: Compartir plugins entre usuarios
3. **UI builder**: Generar UI automáticamente desde `config_schema`
4. **Multi-pane support**: Paneles separados para osciladores
5. **Backtesting hooks**: Integrar con sistema de backtesting
6. **Alertas**: Plugins que generen alertas/señales