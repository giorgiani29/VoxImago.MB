# app.py - Vox Imago
# Ponto de entrada principal do aplicativo.
# Inicializa a interface gráfica e exibe a janela principal.

import sys
from PyQt6.QtWidgets import QApplication
from src.ui.ui import DriveFileGalleryApp


def main():
    print('DEBUG: QApplication será criado')
    app = QApplication(sys.argv)
    print('DEBUG: QApplication criado')
    window = DriveFileGalleryApp()
    print('DEBUG: DriveFileGalleryApp instanciado')
    window.show()
    print('DEBUG: window.show() chamado')
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
