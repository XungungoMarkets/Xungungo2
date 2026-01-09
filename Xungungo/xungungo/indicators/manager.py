from typing import Dict, List, Optional

from PySide6 import QtCore

from .base import IndicatorBase
from .kalman import KalmanIndicator


class PluginManager(QtCore.QAbstractListModel):
    PluginIdRole = QtCore.Qt.UserRole + 1
    NameRole = QtCore.Qt.UserRole + 2
    DescriptionRole = QtCore.Qt.UserRole + 3
    EnabledRole = QtCore.Qt.UserRole + 4

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._plugins: List[IndicatorBase] = [KalmanIndicator()]
        self._enabled: Dict[str, bool] = {plugin.id: False for plugin in self._plugins}
        self._configs: Dict[str, Dict] = {
            plugin.id: plugin.default_config() for plugin in self._plugins
        }

    def roleNames(self):
        return {
            self.PluginIdRole: b"pluginId",
            self.NameRole: b"name",
            self.DescriptionRole: b"description",
            self.EnabledRole: b"enabled",
        }

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._plugins)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        plugin = self._plugins[index.row()]
        if role == self.PluginIdRole:
            return plugin.id
        if role == self.NameRole:
            return plugin.name
        if role == self.DescriptionRole:
            return plugin.description
        if role == self.EnabledRole:
            return self._enabled.get(plugin.id, False)
        return None

    def list_plugins(self) -> List[IndicatorBase]:
        return list(self._plugins)

    def get_plugin(self, plugin_id: str) -> Optional[IndicatorBase]:
        for plugin in self._plugins:
            if plugin.id == plugin_id:
                return plugin
        return None

    def is_enabled(self, plugin_id: str) -> bool:
        return self._enabled.get(plugin_id, False)

    def enable(self, plugin_id: str, enabled: bool) -> None:
        if plugin_id not in self._enabled:
            return
        self._enabled[plugin_id] = enabled
        row = self._index_for(plugin_id)
        if row is not None:
            model_index = self.index(row)
            self.dataChanged.emit(model_index, model_index, [self.EnabledRole])

    def config(self, plugin_id: str) -> Dict:
        return self._configs.get(plugin_id, {})

    def set_config(self, plugin_id: str, config_patch: Dict) -> None:
        if plugin_id not in self._configs:
            return
        updated = dict(self._configs[plugin_id])
        updated.update(config_patch)
        self._configs[plugin_id] = updated

    def _index_for(self, plugin_id: str) -> Optional[int]:
        for idx, plugin in enumerate(self._plugins):
            if plugin.id == plugin_id:
                return idx
        return None
