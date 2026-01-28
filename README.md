# Xungungo

A modern desktop stock analysis application built with **PySide6**, **QML**, and **LightweightCharts**.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- **Interactive Charts** - Candlestick charts powered by TradingView's LightweightCharts
- **Real-Time Data** - Live price updates from multiple sources (NASDAQ, Yahoo Finance)
- **Stock Analysis** - Fundamental data including valuation metrics, holders, and analyst recommendations
- **Technical Indicators** - Extensible plugin system for custom indicators
- **Multi-Tab Interface** - Work with multiple tickers simultaneously
- **Symbol Search** - Autocomplete search powered by Yahoo Finance

## Screenshots

*Coming soon*

## Installation

### Requirements

- Python 3.10+ (recommended 3.11)
- Windows OS

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/xungungo.git
cd xungungo

# Install dependencies
pip install -U pip
pip install -e .
```

## Usage

```bash
python run.py
```

### Debug Mode

```bash
set XUNGUNGO_DEBUG=1
python run.py
```

## Architecture

```
xungungo/
├── app.py                    # Application entry point
├── bridge/                   # QML-JavaScript communication
│   └── chart_bridge.py       # QWebChannel bridge for charts
├── controllers/              # Business logic
│   ├── ticker_controller.py  # Chart data management
│   ├── analysis_controller.py# Fundamental data fetching
│   ├── realtime_controller.py# Real-time price polling
│   ├── search_controller.py  # Symbol search
│   └── tab_manager.py        # Multi-tab management
├── core/                     # Core utilities
│   └── logger.py             # Logging configuration
├── data/                     # Data sources
│   ├── yfinance_source.py    # Yahoo Finance historical data
│   ├── yahoo_search.py       # Symbol search client
│   └── realtime/             # Real-time data providers
│       ├── base.py           # Abstract base class
│       ├── nasdaq.py         # NASDAQ data source
│       └── yahoo_realtime.py # Yahoo Finance fallback
├── indicators/               # Technical indicator plugins
│   ├── base.py               # Plugin base class
│   ├── manager.py            # Plugin autodiscovery
│   ├── bollinger.py          # Bollinger Bands
│   ├── fibonacci.py          # Fibonacci Retracements
│   ├── kalman.py             # Kalman Filter
│   └── td_sequential.py      # TD Sequential
└── ui/
    ├── qml/                  # QML user interface
    │   ├── Main.qml          # Main window
    │   ├── components/       # Reusable components
    │   └── pages/            # Tab pages
    └── web/                  # Web-based chart
        ├── index.html        # Chart container
        └── chart.js          # LightweightCharts integration
```

## Technical Indicators

Xungungo includes several built-in indicators:

| Indicator | Description |
|-----------|-------------|
| **Kalman Filter** | Dual fast/slow Kalman filters with fill between |
| **Bollinger Bands** | Standard deviation bands around moving average |
| **Fibonacci** | Automatic swing detection with retracement levels |
| **TD Sequential** | Tom DeMark's Sequential indicator |

### Creating Custom Indicators

The plugin system uses autodiscovery. Simply add a `.py` file to `xungungo/indicators/`:

```python
from .base import IndicatorPlugin
import pandas as pd

class MyIndicatorPlugin(IndicatorPlugin):
    id = "my_indicator"
    name = "My Indicator"
    description = "Custom indicator description"

    def default_config(self):
        return {"period": 14}

    def apply(self, df: pd.DataFrame, config: dict) -> pd.DataFrame:
        df = df.copy()
        df["my_value"] = df["close"].rolling(config["period"]).mean()
        return df

    def chart_series(self):
        return [{"id": "my_value", "column": "my_value", "type": "line", "pane": "main"}]
```

See [indicators/README.md](xungungo/indicators/README.md) for detailed documentation.

## Real-Time Data

The application supports multiple real-time data sources with automatic fallback:

1. **NASDAQ** - Primary source for US stocks
2. **Yahoo Finance** - Fallback source

Features:
- Configurable polling interval (15s default)
- Exponential backoff on errors
- Rate limit detection and handling
- Smart source caching per symbol

## Tabs

| Tab | Description |
|-----|-------------|
| **Chart** | Interactive candlestick chart with indicators |
| **Analysis** | Fundamental data, holders, recommendations |
| **Options** | Options chain data *(coming soon)* |

## Configuration

### LightweightCharts (Offline Mode)

By default, LightweightCharts loads from CDN. For offline use:

1. Download `lightweight-charts.standalone.production.js`
2. Copy to `xungungo/ui/web/`
3. Update `index.html` to reference the local file

## Development

### Running Tests

```bash
pytest
```

### Project Structure

The application follows a clean separation of concerns:

- **Controllers** handle business logic and data fetching
- **QML** manages the user interface
- **Bridge** enables communication between QML and JavaScript charts
- **Plugins** provide extensibility for technical indicators

## Dependencies

| Package | Purpose |
|---------|---------|
| PySide6 | Qt bindings for Python |
| pandas | Data manipulation |
| numpy | Numerical operations |
| yfinance | Yahoo Finance API |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [TradingView LightweightCharts](https://github.com/tradingview/lightweight-charts) for the charting library
- [yfinance](https://github.com/ranaroussi/yfinance) for market data
- [PySide6](https://doc.qt.io/qtforpython/) for the Qt framework
