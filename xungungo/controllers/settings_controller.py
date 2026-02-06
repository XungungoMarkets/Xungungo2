"""Settings controller for managing application configuration."""
from __future__ import annotations
import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot, Property

from xungungo.core.logger import get_logger


class SettingsController(QObject):
    """Controller for application settings with JSON persistence."""

    # Signals for QML binding
    settingsChanged = Signal()
    themeChanged = Signal(str)

    # Default settings
    DEFAULTS = {
        "theme": "dark",
        "defaultInterval": "1d",
        "defaultPeriod": "1y",
        "datasource": "yfinance",
        "autoRefreshEnabled": True,
        "autoRefreshInterval": 30,  # seconds
        "restoreTabsOnStart": True,
    }

    # Available options for each setting
    AVAILABLE_THEMES = ["dark", "light"]
    AVAILABLE_INTERVALS = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk"]
    AVAILABLE_PERIODS = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]
    AVAILABLE_DATASOURCES = ["yfinance"]  # Expandable in future

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.log = get_logger("xungungo.settings")

        # Settings file path
        self._settings_dir = Path.home() / ".xungungo"
        self._settings_file = self._settings_dir / "settings.json"

        # Current settings
        self._settings: dict = {}

        # Load settings from file
        self._load_settings()

    def _load_settings(self) -> None:
        """Load settings from JSON file, using defaults for missing values."""
        self._settings = self.DEFAULTS.copy()

        if self._settings_file.exists():
            try:
                saved = json.loads(self._settings_file.read_text(encoding="utf-8"))
                # Merge saved settings with defaults (defaults fill missing keys)
                for key, value in saved.items():
                    if key in self.DEFAULTS:
                        self._settings[key] = value
                self.log.info(f"Settings loaded from {self._settings_file}")
            except Exception as e:
                self.log.error(f"Failed to load settings: {e}")
        else:
            self.log.info("No settings file found, using defaults")

    def _save_settings(self) -> None:
        """Save current settings to JSON file."""
        try:
            self._settings_dir.mkdir(parents=True, exist_ok=True)
            self._settings_file.write_text(
                json.dumps(self._settings, indent=2),
                encoding="utf-8"
            )
            self.log.debug("Settings saved")
        except Exception as e:
            self.log.error(f"Failed to save settings: {e}")

    # ─────────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────────
    @Property(str, notify=settingsChanged)
    def theme(self) -> str:
        return self._settings.get("theme", "dark")

    @Slot(str)
    def setTheme(self, value: str) -> None:
        if value in self.AVAILABLE_THEMES and value != self._settings["theme"]:
            self._settings["theme"] = value
            self._save_settings()
            self.themeChanged.emit(value)
            self.settingsChanged.emit()

    @Property("QVariantList", constant=True)
    def availableThemes(self) -> list[str]:
        return self.AVAILABLE_THEMES

    # ─────────────────────────────────────────────────────────────────
    # Default Interval
    # ─────────────────────────────────────────────────────────────────
    @Property(str, notify=settingsChanged)
    def defaultInterval(self) -> str:
        return self._settings.get("defaultInterval", "1d")

    @Slot(str)
    def setDefaultInterval(self, value: str) -> None:
        if value in self.AVAILABLE_INTERVALS and value != self._settings["defaultInterval"]:
            self._settings["defaultInterval"] = value
            self._save_settings()
            self.settingsChanged.emit()

    @Property("QVariantList", constant=True)
    def availableIntervals(self) -> list[str]:
        return self.AVAILABLE_INTERVALS

    # ─────────────────────────────────────────────────────────────────
    # Default Period
    # ─────────────────────────────────────────────────────────────────
    @Property(str, notify=settingsChanged)
    def defaultPeriod(self) -> str:
        return self._settings.get("defaultPeriod", "1y")

    @Slot(str)
    def setDefaultPeriod(self, value: str) -> None:
        if value in self.AVAILABLE_PERIODS and value != self._settings["defaultPeriod"]:
            self._settings["defaultPeriod"] = value
            self._save_settings()
            self.settingsChanged.emit()

    @Property("QVariantList", constant=True)
    def availablePeriods(self) -> list[str]:
        return self.AVAILABLE_PERIODS

    # ─────────────────────────────────────────────────────────────────
    # Datasource
    # ─────────────────────────────────────────────────────────────────
    @Property(str, notify=settingsChanged)
    def datasource(self) -> str:
        return self._settings.get("datasource", "yfinance")

    @Slot(str)
    def setDatasource(self, value: str) -> None:
        if value in self.AVAILABLE_DATASOURCES and value != self._settings["datasource"]:
            self._settings["datasource"] = value
            self._save_settings()
            self.settingsChanged.emit()

    @Property("QVariantList", constant=True)
    def availableDatasources(self) -> list[str]:
        return self.AVAILABLE_DATASOURCES

    # ─────────────────────────────────────────────────────────────────
    # Auto Refresh
    # ─────────────────────────────────────────────────────────────────
    @Property(bool, notify=settingsChanged)
    def autoRefreshEnabled(self) -> bool:
        return self._settings.get("autoRefreshEnabled", True)

    @Slot(bool)
    def setAutoRefreshEnabled(self, value: bool) -> None:
        if value != self._settings["autoRefreshEnabled"]:
            self._settings["autoRefreshEnabled"] = value
            self._save_settings()
            self.settingsChanged.emit()

    @Property(int, notify=settingsChanged)
    def autoRefreshInterval(self) -> int:
        return self._settings.get("autoRefreshInterval", 30)

    @Slot(int)
    def setAutoRefreshInterval(self, value: int) -> None:
        if 5 <= value <= 300 and value != self._settings["autoRefreshInterval"]:
            self._settings["autoRefreshInterval"] = value
            self._save_settings()
            self.settingsChanged.emit()

    # ─────────────────────────────────────────────────────────────────
    # Restore Tabs
    # ─────────────────────────────────────────────────────────────────
    @Property(bool, notify=settingsChanged)
    def restoreTabsOnStart(self) -> bool:
        return self._settings.get("restoreTabsOnStart", True)

    @Slot(bool)
    def setRestoreTabsOnStart(self, value: bool) -> None:
        if value != self._settings["restoreTabsOnStart"]:
            self._settings["restoreTabsOnStart"] = value
            self._save_settings()
            self.settingsChanged.emit()

    # ─────────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────────
    @Slot()
    def resetToDefaults(self) -> None:
        """Reset all settings to defaults."""
        self._settings = self.DEFAULTS.copy()
        self._save_settings()
        self.settingsChanged.emit()
        self.themeChanged.emit(self._settings["theme"])
        self.log.info("Settings reset to defaults")

    @Slot(result=str)
    def getSettingsJson(self) -> str:
        """Get all settings as JSON string for debugging."""
        return json.dumps(self._settings, indent=2)
