import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from xungungo.app import App

def main():
    # Importante: inicializar WebEngine antes de instanciar QGuiApplication
    QtWebEngineQuick.initialize()
    QQuickStyle.setStyle("Fusion")
    app = QGuiApplication(sys.argv)
    xapp = App()
    xapp.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
