# main.py - Vox Imago
# Ponto de entrada alternativo do aplicativo.
# Inicializa o QApplication e exibe a interface principal (DriveFileGalleryApp).

from ui import DriveFileGalleryApp
from PyQt6.QtWidgets import QApplication
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DriveFileGalleryApp()
    ex.show()
    sys.exit(app.exec())