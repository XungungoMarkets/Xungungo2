from __future__ import annotations
import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot

from xungungo.core.logger import get_logger


class TabManager(QObject):
    """Gestiona el estado de múltiples tabs de la aplicación."""

    tabsChanged = Signal(str)  # JSON: [{id, title}, ...]
    currentTabIndexChanged = Signal(int)
    tabClosed = Signal(str)  # Emits tab_id when a tab is closed (for cleanup)

    def __init__(self):
        super().__init__()
        self.log = get_logger("xungungo.tab_manager")
        self._tabs = []  # [{id: str, title: str, symbol: str}]
        self._current_index = 0
        self._next_id = 0
        self._state_file = Path.home() / ".xungungo" / "tabs_state.json"
        self._load_state()

        # Garantizar al menos un tab
        if not self._tabs:
            self._add_initial_tab()

    @Slot(result=str)
    def getTabs(self) -> str:
        """Retorna la lista de tabs como JSON."""
        return json.dumps(self._tabs)

    @Slot(result=int)
    def getCurrentIndex(self) -> int:
        """Retorna el índice del tab actual."""
        return self._current_index

    @Slot(result=int)
    def addTab(self) -> int:
        """Crea un nuevo tab vacío y retorna su índice."""
        tab_id = f"tab_{self._next_id}"
        self._next_id += 1

        new_tab = {"id": tab_id, "title": "Empty", "symbol": ""}
        self._tabs.append(new_tab)
        index = len(self._tabs) - 1

        self.log.info(f"Added new tab: {tab_id} at index {index}")
        self.tabsChanged.emit(self.getTabs())
        self._save_state()

        return index

    @Slot(str, result=int)
    def addTabWithSymbol(self, symbol: str) -> int:
        """Crea un nuevo tab con un símbolo específico y retorna su índice."""
        tab_id = f"tab_{self._next_id}"
        self._next_id += 1

        new_tab = {"id": tab_id, "title": symbol or "Empty", "symbol": symbol}
        self._tabs.append(new_tab)
        index = len(self._tabs) - 1

        self.log.info(f"Added new tab with symbol: {tab_id} ({symbol}) at index {index}")
        self.tabsChanged.emit(self.getTabs())
        self._save_state()

        return index

    @Slot(int)
    def closeTab(self, index: int):
        """Cierra el tab en el índice dado (si no es el único)."""
        if len(self._tabs) <= 1:
            self.log.warning("Cannot close the last tab")
            return  # No cerrar el último tab

        if 0 <= index < len(self._tabs):
            removed_tab = self._tabs.pop(index)
            removed_tab_id = removed_tab['id']
            self.log.info(f"Closed tab at index {index}: {removed_tab_id}")

            # Emit tabClosed signal for cleanup (before adjusting index)
            self.tabClosed.emit(removed_tab_id)

            # Ajustar índice actual si es necesario
            if self._current_index >= len(self._tabs):
                self._current_index = len(self._tabs) - 1
            elif self._current_index > index:
                self._current_index -= 1

            self.tabsChanged.emit(self.getTabs())
            self.currentTabIndexChanged.emit(self._current_index)
            self._save_state()

    @Slot(int)
    def setCurrentTab(self, index: int):
        """Cambia el tab activo."""
        if 0 <= index < len(self._tabs):
            self._current_index = index
            self.log.debug(f"Current tab changed to index {index}")
            self.currentTabIndexChanged.emit(index)
            self._save_state()

    @Slot(int, str)
    def setTabTitle(self, index: int, title: str):
        """Actualiza el título de un tab."""
        if 0 <= index < len(self._tabs):
            self._tabs[index]["title"] = title or "Empty"
            self.log.debug(f"Tab {index} title updated to: {title}")
            self.tabsChanged.emit(self.getTabs())
            self._save_state()

    @Slot(int, str)
    def setTabSymbol(self, index: int, symbol: str):
        """Actualiza el símbolo de un tab (y su título si el símbolo no está vacío)."""
        if 0 <= index < len(self._tabs):
            self._tabs[index]["symbol"] = symbol
            if symbol:
                self._tabs[index]["title"] = symbol
            else:
                self._tabs[index]["title"] = "Empty"
            self.log.debug(f"Tab {index} symbol updated to: {symbol}")
            self.tabsChanged.emit(self.getTabs())
            self._save_state()

    @Slot(int, result=str)
    def getTabSymbol(self, index: int) -> str:
        """Retorna el símbolo del tab en el índice dado."""
        if 0 <= index < len(self._tabs):
            return self._tabs[index].get("symbol", "")
        return ""

    @Slot(int, result=str)
    def getTabId(self, index: int) -> str:
        """Retorna el ID del tab en el índice dado."""
        if 0 <= index < len(self._tabs):
            return self._tabs[index]["id"]
        return ""

    def _add_initial_tab(self):
        """Agrega el primer tab inicial."""
        self._tabs = [{"id": "tab_0", "title": "Empty", "symbol": ""}]
        self._next_id = 1
        self.log.info("Created initial tab")

    def _save_state(self):
        """Persiste el estado de los tabs."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "tabs": self._tabs,
                "currentIndex": self._current_index,
                "nextId": self._next_id
            }
            self._state_file.write_text(json.dumps(state, indent=2))
            self.log.debug("Tab state saved")
        except Exception as e:
            self.log.error(f"Failed to save tab state: {e}")

    def _load_state(self):
        """Carga el estado de los tabs desde disco."""
        if self._state_file.exists():
            try:
                state = json.loads(self._state_file.read_text())
                self._tabs = state.get("tabs", [])
                self._current_index = state.get("currentIndex", 0)
                self._next_id = state.get("nextId", len(self._tabs))

                # Migrate old tabs without symbol field
                for tab in self._tabs:
                    if "symbol" not in tab:
                        # If title is not "Empty", assume it's the symbol
                        if tab.get("title", "Empty") != "Empty":
                            tab["symbol"] = tab["title"]
                        else:
                            tab["symbol"] = ""

                self.log.info(f"Loaded {len(self._tabs)} tabs from saved state")
            except Exception as e:
                self.log.error(f"Failed to load tab state: {e}")
                # Si falla, se creará un tab inicial
