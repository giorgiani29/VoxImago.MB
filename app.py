# app.py - Vox Imago
# Ponto de entrada principal do aplicativo.
# Inicializa a interface gráfica e exibe a janela principal.

import sys
from PyQt6.QtWidgets import QApplication
from src.ui import DriveFileGalleryApp


def main():
    app = QApplication(sys.argv)
    window = DriveFileGalleryApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
