# Xungungo (PySide6 + QML + LightweightCharts + Plugins)

## Requisitos
- Python 3.10+ (recomendado 3.11)
- Windows (sin empaquetado)

## Instalación
Desde la carpeta del proyecto:

```bash
pip install -U pip
pip install -e .
```

> Alternativa: `pip install .` (sin editable)

## Ejecución
```bash
python run.py
```

## Arquitectura (resumen)
- `xungungo/data`: datasources (por ahora yfinance) y normalización a OHLCV estándar.
- `xungungo/indicators`: sistema de plugins de indicadores (base + manager + Kalman).
- `xungungo/ui/qml`: UI principal (sidebar + página Ticker).
- `xungungo/ui/web`: `index.html` + `chart.js` con LightweightCharts (cargado vía CDN por defecto).
- `xungungo/bridge`: `ChartBridge(QObject)` expuesto al JS vía `QWebChannel`.
- `xungungo/controllers`: coordina datasource + plugins + chart.

## Nota sobre LightweightCharts (offline)
Por limitaciones del entorno donde se generó este zip, **LightweightCharts se carga desde CDN** en `xungungo/ui/web/index.html`.

Si necesitas modo offline, reemplaza el `<script src="...">` por un archivo local:
- Descarga `lightweight-charts.standalone.production.js`
- Cópialo a `xungungo/ui/web/`
- Actualiza `index.html` para referenciarlo localmente.

## Agregar un nuevo indicador plugin
1. Crea `xungungo/indicators/<tu_indicador>.py` implementando `IndicatorPlugin`.
2. Regístralo en `xungungo/indicators/manager.py`.
3. Expón su toggle + configuración en QML (o extiende para UI dinámica con schema).
4. Implementa `chart_series()` para describir qué columnas se dibujan.

