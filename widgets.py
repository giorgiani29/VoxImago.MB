# widgets.py - Componentes visuais customizados do Vox Imago
# Inclui FileItemWidget, OptionsDialog, ClickableLabel
# Use este arquivo para importar widgets personalizados na interface principal.

import os
import sys
import sqlite3
import webbrowser
import cv2
import platform

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QMessageBox, QApplication, QDialog, QDialogButtonBox, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QUrl, QThreadPool, QRunnable, QObject
from PyQt6.QtGui import QPixmap, QFont, QPalette, QDrag, QImage, QPainter, QColor


from utils import get_generic_thumbnail, format_size

from workers import ThumbnailWorker
from utils import load_settings, get_thumbnail_cache_key

THUMBNAIL_CACHE_DIR = "thumbnail_cache"


class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opções de Escaneamento Local")
        self.setModal(True)
        self.setFixedSize(400, 300)

        self.main_layout = QVBoxLayout(self)

        self.label = QLabel("Selecione as pastas a serem escaneadas:")
        self.main_layout.addWidget(self.label)

        self.checkboxes = {}
        self.default_paths = self._get_default_folders()

        saved_settings = load_settings().get('scan_paths', [])

        for name, path in self.default_paths.items():
            checkbox = QCheckBox(f"{name} ({path})")
            if path in saved_settings:
                checkbox.setChecked(True)
            self.checkboxes[name] = checkbox
            self.main_layout.addWidget(checkbox)

        self.custom_folder_button = QPushButton("Adicionar Outra Pasta...")
        self.custom_folder_button.clicked.connect(self._add_custom_folder)
        self.main_layout.addWidget(self.custom_folder_button)

        self.custom_paths = saved_settings

        for path in saved_settings:
            if path not in self.default_paths.values():
                checkbox = QCheckBox(f"Customizada: {path}")
                checkbox.setChecked(True)
                self.checkboxes[path] = checkbox
                self.main_layout.insertWidget(
                    self.main_layout.count() - 2, checkbox)

        settings = load_settings()
        show_drive_metadata = settings.get('show_drive_metadata', True)
        self.drive_metadata_checkbox = QCheckBox("Exibir metadados do Drive")
        self.drive_metadata_checkbox.setChecked(show_drive_metadata)
        self.main_layout.addWidget(self.drive_metadata_checkbox)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.main_layout.addWidget(self.button_box)

    def get_show_drive_metadata(self):
        return self.drive_metadata_checkbox.isChecked()

    def _get_default_folders(self):
        user_home = os.path.expanduser("~")
        if platform.system() == "Windows":
            return {
                "Documentos": os.path.join(user_home, "Documents"),
                "Imagens": os.path.join(user_home, "Pictures"),
                "Música": os.path.join(user_home, "Music"),
                "Vídeos": os.path.join(user_home, "Videos"),
                "Downloads": os.path.join(user_home, "Downloads"),
                "Desktop": os.path.join(user_home, "Desktop")
            }
        elif platform.system() == "Darwin":
            return {
                "Documentos": os.path.join(user_home, "Documents"),
                "Imagens": os.path.join(user_home, "Pictures"),
                "Música": os.path.join(user_home, "Music"),
                "Filmes": os.path.join(user_home, "Movies"),
                "Downloads": os.path.join(user_home, "Downloads"),
                "Desktop": os.path.join(user_home, "Desktop")
            }
        else:
            return {
                "Documentos": os.path.join(user_home, "Documents"),
                "Imagens": os.path.join(user_home, "Pictures"),
                "Música": os.path.join(user_home, "Music"),
                "Vídeos": os.path.join(user_home, "Videos"),
                "Downloads": os.path.join(user_home, "Downloads"),
                "Desktop": os.path.join(user_home, "Desktop")
            }

    def _add_custom_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Selecione a Pasta para Adicionar")
        if folder_path and folder_path not in self.custom_paths:
            self.custom_paths.append(folder_path)
            checkbox = QCheckBox(f"Customizada: {folder_path}")
            checkbox.setChecked(True)
            self.checkboxes[folder_path] = checkbox
            self.main_layout.insertWidget(
                self.main_layout.count() - 2, checkbox)

    def get_selected_paths(self):
        selected_paths = []
        for name, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                path = self.default_paths.get(name) or name
                selected_paths.append(path)
        return selected_paths

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

class ThumbnailTask(QRunnable):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker

    def run(self):
        self.worker.run()
