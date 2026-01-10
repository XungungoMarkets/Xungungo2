import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from xungungo.app import App

def main():
    # Importante: inicializar WebEngine antes de instanciar QGuiApplication
    QtWebEngineQuick.initialize()
    app = QGuiApplication(sys.argv)
    xapp = App()
    xapp.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
