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


class FileItemWidget(QFrame):
    selected = pyqtSignal(object)
    folder_clicked = pyqtSignal(str)

    def cleanup(self):
        pass

    def __init__(self, parent_app, file_item, service, status_bar_callback):
        super().__init__()
        self.parent_app = parent_app
        self.file_item = file_item
        self.service = service
        self.status_bar_callback = status_bar_callback
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setFixedHeight(60)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Sempre exibe ícone genérico
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(48, 48)
        pixmap = get_generic_thumbnail(self.file_item.get('mimeType'))
        if pixmap:
            pixmap = pixmap.scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.thumbnail_label.setPixmap(pixmap)
        self.main_layout.addWidget(self.thumbnail_label)

        self.name_label = QLabel(
            self.file_item.get('name', 'Nome Desconhecido'))
        self.name_label.setFont(QFont("Arial", 10))
        self.name_label.setWordWrap(False)

        # Mostra status local/remoto para arquivos do Drive
        if self.file_item.get('source') == 'drive':
            local_path = self.file_item.get('path')
            if local_path and os.path.exists(local_path):
                source_name = "Drive (Local)"
            else:
                source_name = "Drive (Somente Metadados)"
        else:
            source_name = "Local"
        self.source_label = QLabel(f"({source_name})")
        self.source_label.setFont(QFont("Arial", 8))
        self.source_label.setStyleSheet("color: gray;")

        self.apply_theme_style()

        self.main_layout.addSpacing(15)

        name_source_layout = QVBoxLayout()
        name_source_layout.addWidget(self.name_label)
        name_source_layout.addWidget(self.source_label)
        name_source_layout.setSpacing(0)

        self.main_layout.addLayout(name_source_layout, 1)
        self.main_layout.addStretch()
        self.main_layout.setContentsMargins(10, 5, 10, 5)

        self.local_file_path = self.file_item.get('path')

        self.star_button = QPushButton(
            "★" if self.parent_app.indexer.is_starred(self.file_item.get('id')) else "☆")
        self.star_button.setFixedWidth(30)
        self.star_button.setStyleSheet(
            "font-size: 18px; border: none; background: transparent;")
        self.star_button.clicked.connect(self.toggle_starred)
        self.main_layout.addWidget(self.star_button)

    # Miniatura já exibida acima

    def toggle_starred(self):
        is_now_starred = not self.parent_app.indexer.is_starred(
            self.file_item.get('id'))
        self.parent_app.indexer.set_starred(
            self.file_item.get('id'), is_now_starred)
        self.star_button.setText("★" if is_now_starred else "☆")
        self.status_bar_callback(
            "Marcado como favorito." if is_now_starred else "Desmarcado como favorito.")

    def apply_theme_style(self):
        bg_color = QApplication.palette().color(QPalette.ColorRole.Window)
        luminosity = 0.299 * bg_color.red() + 0.587 * bg_color.green() + \
            0.114 * bg_color.blue()
        text_color = "white" if luminosity < 128 else "black"
        self.name_label.setStyleSheet(f"color: {text_color};")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.file_item.get('mimeType') == 'application/vnd.google-apps.folder' or self.file_item.get('mimeType') == 'folder':
                self.folder_clicked.emit(self.file_item.get('id'))
            else:
                # Se for arquivo do Drive, apenas seleciona para busca local
                self.selected.emit(self.file_item)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self.file_item.get('mimeType') != 'application/vnd.google-apps.folder' and self.file_item.get('mimeType') != 'folder':
                self.do_drag()
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.file_item.get('mimeType') == 'application/vnd.google-apps.folder' or self.file_item.get('mimeType') == 'folder':
                self.folder_clicked.emit(self.file_item.get('id'))
            else:
                # Se for arquivo do Drive, apenas seleciona para busca local
                self.selected.emit(self.file_item)

    def open_file(self):
        file_source = self.file_item.get('source')
        file_path = self.file_item.get('path')

        if file_source == 'local' or (file_source == 'drive' and file_path and os.path.exists(file_path)):
            try:
                if sys.platform == "win32":
                    os.startfile(file_path)
                else:
                    webbrowser.open_new_tab(f'file:///{file_path}')
            except Exception as e:
                QMessageBox.critical(
                    self, "Erro ao Abrir Arquivo", f"Não foi possível abrir o arquivo: {e}")
        elif file_source == 'drive':
            QMessageBox.information(
                self, "Arquivo do Drive", "Apenas metadados disponíveis para busca local.")

    # Função de download removida

    def do_drag(self):
        if self.file_item.get('source') == 'local' or (self.local_file_path and os.path.exists(self.local_file_path)):
            drag = QDrag(self)
            mime_data = QMimeData()
            urls = [QUrl.fromLocalFile(self.local_file_path)]
            mime_data.setUrls(urls)
            drag.setMimeData(mime_data)

            # Usa ícone genérico para o tipo de arquivo
            pixmap = get_generic_thumbnail(self.file_item.get('mimeType'))
            if pixmap:
                drag.setPixmap(pixmap)
                drag.setHotSpot(pixmap.rect().center())

            drag.exec(Qt.DropAction.CopyAction)
            return

        mime_type = self.file_item.get('mimeType')
        file_size = self.file_item.get('size', 0)
        is_small_file = file_size < 5 * 1024 * 1024

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.file_item.get('name'))
        drag.setMimeData(mime_data)

        # Usa ícone genérico para o tipo de arquivo
        pixmap = get_generic_thumbnail(self.file_item.get('mimeType'))
        if pixmap:
            drag.setPixmap(pixmap)
            drag.setHotSpot(pixmap.rect().center())

        drag.exec(Qt.DropAction.CopyAction)

        # Download removido: não permite arrastar arquivos do Drive

    # Função de download removida


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

        # Checkbox for Drive metadata
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
