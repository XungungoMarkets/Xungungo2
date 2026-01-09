from PySide6 import QtCore


class ChartBridge(QtCore.QObject):
    setCandles = QtCore.Signal(str)
    setIndicatorSeries = QtCore.Signal(str, str)
    setIndicatorVisible = QtCore.Signal(str, bool)
    reset = QtCore.Signal()
    ready = QtCore.Signal()

    @QtCore.Slot()
    def onReady(self) -> None:
        self.ready.emit()
