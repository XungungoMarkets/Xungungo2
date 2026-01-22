from __future__ import annotations
import importlib
import inspect
import pkgutil
import json
from pathlib import Path
from typing import Any
import pandas as pd

from xungungo.core.logger import get_logger
from .base import IndicatorPlugin


class PluginManager:
    def __init__(self):
        self._plugins: dict[str, IndicatorPlugin] = {}
        self._enabled: dict[str, bool] = {}
        self._configs: dict[str, dict[str, Any]] = {}
        self._current_preset_id: dict[str, str] = {}
        self._custom_presets: dict[str, dict[str, dict[str, Any]]] = {}  # plugin_id -> {preset_id: preset_data}
        self._chart_state: dict[str, dict[str, Any]] = {}  # ticker -> chart state (timeframe + indicators)
        self.log = get_logger("xungungo.plugins")

        # Autodiscovery de plugins
        self._discover_plugins()
        self._load_custom_presets()
        self._load_chart_state()

    def _discover_plugins(self) -> None:
        """
        Descubre automáticamente todos los plugins en la carpeta indicators.
        Busca clases que hereden de IndicatorPlugin y las registra.
        """
        # Obtener el path del módulo indicators
        indicators_path = Path(__file__).parent
        package_name = __package__ or "xungungo.indicators"

        self.log.info(f"Discovering plugins in: {indicators_path}")

        # Iterar sobre todos los módulos en la carpeta
        for _, module_name, is_pkg in pkgutil.iter_modules([str(indicators_path)]):
            # Saltar base.py y manager.py
            if module_name in ("base", "manager", "__init__"):
                continue

            # Saltar paquetes (subdirectorios)
            if is_pkg:
                continue

            try:
                # Importar el módulo
                full_module_name = f"{package_name}.{module_name}"
                module = importlib.import_module(full_module_name)

                # Buscar clases que hereden de IndicatorPlugin
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Verificar que herede de IndicatorPlugin y no sea la clase base
                    if (
                        issubclass(obj, IndicatorPlugin)
                        and obj is not IndicatorPlugin
                        and hasattr(obj, "id")
                    ):
                        # Instanciar y registrar
                        try:
                            plugin_instance = obj()
                            self.register(plugin_instance)
                            self.log.info(f"Registered plugin: {plugin_instance.id} ({plugin_instance.name})")
                        except Exception as e:
                            self.log.error(f"Failed to instantiate {name}: {e}")

            except Exception as e:
                self.log.error(f"Failed to load module {module_name}: {e}")

        self.log.info(f"Plugin discovery complete. Loaded {len(self._plugins)} plugins.")

    def register(self, plugin: IndicatorPlugin) -> None:
        """Registra un plugin manualmente (útil para testing o plugins externos)."""
        self._plugins[plugin.id] = plugin
        self._enabled.setdefault(plugin.id, False)
        self._configs.setdefault(plugin.id, plugin.default_config())
        self._current_preset_id.setdefault(plugin.id, "")

    def list_plugins(self) -> list[dict[str, Any]]:
        out = []
        for pid, p in self._plugins.items():
            cfg = self._configs.get(pid, {})

            # Combine built-in presets with custom presets
            built_in_presets = p.presets()
            custom_presets = self._custom_presets.get(pid, {})
            all_presets = {**built_in_presets, **custom_presets}

            out.append({
                "id": pid,
                "name": p.name,
                "description": p.description,
                "enabled": self._enabled.get(pid, False),
                "schema": p.config_schema(),
                "config": cfg,
                "chart_series": p.chart_series(cfg),  # Pass config to get dynamic series
                "presets": all_presets,
                "current_preset_id": self._current_preset_id.get(pid, ""),
            })
        return out

    def enable(self, plugin_id: str, enabled: bool) -> None:
        """Enable or disable a plugin by ID."""
        if plugin_id in self._plugins:
            self._enabled[plugin_id] = bool(enabled)

    def set_config(self, plugin_id: str, patch: dict[str, Any]) -> None:
        """Update configuration for a specific plugin."""
        if plugin_id not in self._plugins:
            return
        cfg = self._configs.get(plugin_id, {}).copy()
        # shallow merge for simplicity
        for k, v in patch.items():
            cfg[k] = v
        self._configs[plugin_id] = cfg
        self._current_preset_id[plugin_id] = ""

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all enabled plugins to the DataFrame.
        Each plugin is isolated - if one fails, others continue executing.

        Optimization: Only makes one initial copy, then reuses the same DataFrame
        across plugins to minimize memory allocation.
        """
        # Single copy at the start
        out = df.copy()

        for pid, plugin in self._plugins.items():
            if self._enabled.get(pid, False):
                try:
                    # Plugin applies transformations and returns modified DataFrame
                    # Most plugins add columns, so the same object can be reused
                    out = plugin.apply(out, self._configs.get(pid, {}))
                except Exception as e:
                    # Log error but continue with other plugins
                    self.log.error(f"Plugin '{pid}' failed: {e}", exc_info=True)
                    # Optionally disable the failing plugin to prevent repeated errors
                    self._enabled[pid] = False
                    self.log.warning(f"Plugin '{pid}' has been disabled due to error")

        return out

    def enabled_plugins(self) -> list[str]:
        """Return list of enabled plugin IDs."""
        return [pid for pid, en in self._enabled.items() if en]

    def get_config(self, plugin_id: str) -> dict[str, Any]:
        """Get configuration for a specific plugin."""
        return self._configs.get(plugin_id, {}).copy()

    def get_plugin(self, plugin_id: str) -> IndicatorPlugin | None:
        return self._plugins.get(plugin_id)

    def reload_plugins(self) -> None:
        """
        Recarga todos los plugins (útil durante desarrollo).
        Preserva configuraciones pero re-descubre los plugins.
        """
        old_configs = self._configs.copy()
        old_enabled = self._enabled.copy()
        old_presets = self._current_preset_id.copy()

        self._plugins.clear()
        self._enabled.clear()
        self._configs.clear()
        self._current_preset_id.clear()

        self._discover_plugins()

        # Restaurar configuraciones previas si el plugin sigue existiendo
        for pid in self._plugins.keys():
            if pid in old_configs:
                self._configs[pid] = old_configs[pid]
            if pid in old_enabled:
                self._enabled[pid] = old_enabled[pid]
            if pid in old_presets:
                self._current_preset_id[pid] = old_presets[pid]

    def _get_presets_file(self) -> Path:
        """Get path to custom presets file."""
        return Path.home() / ".xungungo" / "custom_presets.json"

    def _load_custom_presets(self) -> None:
        """Load custom presets from file."""
        presets_file = self._get_presets_file()
        if not presets_file.exists():
            return

        try:
            with open(presets_file, "r", encoding="utf-8") as f:
                self._custom_presets = json.load(f)
            self.log.info(f"Loaded custom presets from {presets_file}")
        except Exception as e:
            self.log.error(f"Failed to load custom presets: {e}")
            self._custom_presets = {}

    def _save_custom_presets(self) -> None:
        """Save custom presets to file."""
        presets_file = self._get_presets_file()
        presets_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(presets_file, "w", encoding="utf-8") as f:
                json.dump(self._custom_presets, f, indent=2)
            self.log.info(f"Saved custom presets to {presets_file}")
        except Exception as e:
            self.log.error(f"Failed to save custom presets: {e}")

    def add_custom_preset(self, plugin_id: str, preset_id: str, name: str, description: str, config: dict[str, Any]) -> bool:
        """
        Add a custom preset for a plugin.

        Args:
            plugin_id: ID of the plugin
            preset_id: Unique ID for this preset (e.g., "my_custom_scalping")
            name: Display name
            description: Description of what this preset does
            config: Configuration values

        Returns:
            True if successful, False otherwise
        """
        if plugin_id not in self._plugins:
            self.log.error(f"Plugin {plugin_id} not found")
            return False

        # Check if preset_id conflicts with built-in presets
        built_in_presets = self._plugins[plugin_id].presets()
        if preset_id in built_in_presets:
            self.log.error(f"Cannot override built-in preset: {preset_id}")
            return False

        if plugin_id not in self._custom_presets:
            self._custom_presets[plugin_id] = {}

        self._custom_presets[plugin_id][preset_id] = {
            "name": name,
            "description": description,
            "config": config,
            "custom": True,  # Mark as custom to allow deletion
        }

        self._save_custom_presets()
        return True

    def delete_custom_preset(self, plugin_id: str, preset_id: str) -> bool:
        """
        Delete a custom preset.

        Args:
            plugin_id: ID of the plugin
            preset_id: ID of the preset to delete

        Returns:
            True if successful, False otherwise
        """
        if plugin_id not in self._custom_presets:
            return False

        if preset_id not in self._custom_presets[plugin_id]:
            return False

        # Verify it's actually a custom preset
        if not self._custom_presets[plugin_id][preset_id].get("custom", False):
            self.log.error(f"Cannot delete built-in preset: {preset_id}")
            return False

        del self._custom_presets[plugin_id][preset_id]

        # Clean up empty plugin entries
        if not self._custom_presets[plugin_id]:
            del self._custom_presets[plugin_id]

        self._save_custom_presets()
        return True

    def apply_preset(self, plugin_id: str, preset_id: str) -> bool:
        """
        Apply a preset to a plugin's configuration.

        Args:
            plugin_id: ID of the plugin
            preset_id: ID of the preset to apply

        Returns:
            True if successful, False otherwise
        """
        if plugin_id not in self._plugins:
            return False

        # Look for preset in built-in presets first
        plugin = self._plugins[plugin_id]
        built_in_presets = plugin.presets()

        preset = None
        if preset_id in built_in_presets:
            preset = built_in_presets[preset_id]
        elif plugin_id in self._custom_presets and preset_id in self._custom_presets[plugin_id]:
            preset = self._custom_presets[plugin_id][preset_id]

        if not preset or "config" not in preset:
            self.log.error(f"Preset {preset_id} not found for plugin {plugin_id}")
            return False

        # Apply the preset configuration
        self._configs[plugin_id] = preset["config"].copy()
        self._current_preset_id[plugin_id] = preset_id
        self.log.info(f"Applied preset '{preset_id}' to plugin '{plugin_id}'")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Chart State Persistence (per ticker)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_chart_state_file(self) -> Path:
        """Get path to chart state file."""
        return Path.home() / ".xungungo" / "chart_state.json"

    def _load_chart_state(self) -> None:
        """Load chart state from file."""
        state_file = self._get_chart_state_file()
        if not state_file.exists():
            return

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                self._chart_state = json.load(f)
            self.log.info(f"Loaded chart state from {state_file}")
        except Exception as e:
            self.log.error(f"Failed to load chart state: {e}")
            self._chart_state = {}

    def _save_chart_state(self) -> None:
        """Save chart state to file."""
        state_file = self._get_chart_state_file()
        state_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(self._chart_state, f, indent=2)
            self.log.debug(f"Saved chart state to {state_file}")
        except Exception as e:
            self.log.error(f"Failed to save chart state: {e}")

    def save_chart_state_for_ticker(self, ticker: str, interval: str, period: str) -> None:
        """
        Save the current chart configuration for a specific ticker.

        Args:
            ticker: The ticker symbol (e.g., "AAPL", "BTC-USD")
            interval: Current interval (e.g., "1d", "1h")
            period: Current period (e.g., "1y", "1mo")
        """
        if not ticker:
            return

        # Build indicators state
        indicators_state = {}
        for pid in self._plugins.keys():
            indicators_state[pid] = {
                "enabled": self._enabled.get(pid, False),
                "preset_id": self._current_preset_id.get(pid, ""),
                "config": self._configs.get(pid, {}).copy()
            }

        self._chart_state[ticker] = {
            "interval": interval,
            "period": period,
            "indicators": indicators_state
        }

        self._save_chart_state()
        self.log.debug(f"Saved chart state for {ticker}")

    def load_chart_state_for_ticker(self, ticker: str) -> dict[str, Any] | None:
        """
        Load the saved chart configuration for a specific ticker.

        Args:
            ticker: The ticker symbol

        Returns:
            Dict with interval, period, and indicators state, or None if not found
        """
        return self._chart_state.get(ticker)

    def apply_chart_state(self, state: dict[str, Any]) -> None:
        """
        Apply a previously saved chart state to the current session.

        Args:
            state: The chart state dict containing indicators configuration
        """
        indicators_state = state.get("indicators", {})

        for pid, ind_state in indicators_state.items():
            if pid not in self._plugins:
                continue

            # Restore enabled state
            self._enabled[pid] = ind_state.get("enabled", False)

            # Restore config
            saved_config = ind_state.get("config", {})
            if saved_config:
                self._configs[pid] = saved_config.copy()

            # Restore preset ID
            self._current_preset_id[pid] = ind_state.get("preset_id", "")

        self.log.info("Applied saved chart state")

    def get_chart_state_tickers(self) -> list[str]:
        """Get list of tickers with saved chart state."""
        return list(self._chart_state.keys())
