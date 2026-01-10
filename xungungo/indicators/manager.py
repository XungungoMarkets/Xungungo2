from __future__ import annotations
from typing import Dict, Any, List
import pandas as pd

from .base import IndicatorPlugin
from .kalman import KalmanPlugin

class PluginManager:
    def __init__(self):
        self._plugins: Dict[str, IndicatorPlugin] = {}
        self._enabled: Dict[str, bool] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}

        # registro manual inicial
        self.register(KalmanPlugin())

    def register(self, plugin: IndicatorPlugin) -> None:
        self._plugins[plugin.id] = plugin
        self._enabled.setdefault(plugin.id, False)
        self._configs.setdefault(plugin.id, plugin.default_config())

    def list_plugins(self) -> List[Dict[str, Any]]:
        out = []
        for pid, p in self._plugins.items():
            out.append({
                "id": pid,
                "name": p.name,
                "description": p.description,
                "enabled": self._enabled.get(pid, False),
                "schema": p.config_schema(),
                "config": self._configs.get(pid, {}),
                "chart_series": p.chart_series(),
            })
        return out

    def enable(self, plugin_id: str, enabled: bool) -> None:
        if plugin_id in self._plugins:
            self._enabled[plugin_id] = bool(enabled)

    def set_config(self, plugin_id: str, patch: Dict[str, Any]) -> None:
        if plugin_id not in self._plugins:
            return
        cfg = self._configs.get(plugin_id, {}).copy()
        # shallow merge for simplicity
        for k, v in patch.items():
            cfg[k] = v
        self._configs[plugin_id] = cfg

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for pid, plugin in self._plugins.items():
            if self._enabled.get(pid, False):
                out = plugin.apply(out, self._configs.get(pid, {}))
        return out

    def enabled_plugins(self) -> List[str]:
        return [pid for pid, en in self._enabled.items() if en]

    def get_config(self, plugin_id: str) -> Dict[str, Any]:
        return self._configs.get(plugin_id, {}).copy()

    def get_plugin(self, plugin_id: str) -> IndicatorPlugin | None:
        return self._plugins.get(plugin_id)
