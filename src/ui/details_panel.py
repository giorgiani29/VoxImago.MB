# Painel de detalhes do arquivo exibe informações e miniatura.

import os
import sys
import subprocess
import webbrowser
from datetime import datetime
from PyQt6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QLabel, QPushButton, QFormLayout, QScrollArea, QMessageBox
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt
from src.utils.utils import format_size
from src.ui.thumbnails import ThumbnailCache, ThumbnailManager


class FileDetailsPanel(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_loading = False

        self.content_widget = QWidget()
        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.title_label = QLabel("Detalhes do Arquivo")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(400, 400)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.thumbnail_label)

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(self.separator)

        self.form_layout = QFormLayout()
        self.name_label = QLabel("N/A")
        self.source_label = QLabel("N/A")
        self.size_label = QLabel("N/A")
        self.path_label = QLabel("N/A")
        self.path_label.setWordWrap(True)
        self.description_label = QLabel("N/A")
        self.description_label.setWordWrap(True)
        self.created_label = QLabel("N/A")

        self.form_layout.addRow(QLabel("<b>Nome:</b>"), self.name_label)
        self.form_layout.addRow(QLabel("<b>Fonte:</b>"), self.source_label)
        self.form_layout.addRow(QLabel("<b>Tamanho:</b>"), self.size_label)
        self.form_layout.addRow(
            QLabel("<b>Caminho/Link:</b>"), self.path_label)
        self.form_layout.addRow(
            QLabel("<b>Descrição:</b>"), self.description_label)
        self.form_layout.addRow(
            QLabel("<b>Data de criação:</b>"), self.created_label)

        self.open_drive_button = QPushButton("Abrir no Drive")
        self.open_drive_button.setVisible(False)
        self.open_drive_button.clicked.connect(self.open_drive_link)
        self.open_drive_label = QLabel("")
        self.form_layout.addRow(self.open_drive_label, self.open_drive_button)

        self.open_folder_button = QPushButton("Abrir pasta")
        self.open_folder_button.setVisible(False)
        self.open_folder_button.clicked.connect(self.open_folder)
        self.open_folder_label = QLabel("")
        self.form_layout.addRow(self.open_folder_label,
                                self.open_folder_button)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll_area)

        self.current_file_item = None
        self.parent_app = parent
        self.temp_download_widget = None

        self.hide()

    def update_details(self, file_item):
        if hasattr(self, 'thumbnail_thread') and self.thumbnail_thread:
            try:
                if self.thumbnail_thread.isRunning():
                    self.thumbnail_thread.quit()
                    self.thumbnail_thread.wait()
                self.thumbnail_worker.deleteLater()
                self.thumbnail_thread.deleteLater()
            except Exception:
                pass
            self.thumbnail_worker = None
            self.thumbnail_thread = None

        self.title_label.setText("Detalhes do Arquivo")
        self.name_label.setText(file_item.get('name', 'N/A'))
        self.source_label.setText("Google Drive" if file_item.get(
            'source') == 'drive' else "Local")
        self.size_label.setText(format_size(file_item.get('size', 0)) if file_item.get(
            'mimeType') not in ['application/vnd.google-apps.folder', 'folder'] else "N/A")
        raw_path = file_item.get('path', file_item.get('webViewLink', 'N/A'))
        if raw_path and isinstance(raw_path, str):
            display_path = raw_path.replace('\\', '/').replace('\\', '/')
        else:
            display_path = raw_path
        self.path_label.setText(display_path)

        created_timestamp = file_item.get('createdTime')
        if created_timestamp:
            try:
                if isinstance(created_timestamp, (int, float)):
                    created_date = datetime.fromtimestamp(created_timestamp)
                else:
                    created_date = datetime.fromisoformat(
                        str(created_timestamp).replace('Z', '+00:00'))
                created_str = created_date.strftime('%d/%m/%Y')
                self.created_label.setText(created_str)
            except Exception:
                self.created_label.setText(str(created_timestamp))
        else:
            self.created_label.setText("N/A")

        self.description_label.setText(file_item.get('description', 'N/A'))

        self.current_file_item = file_item

        if file_item.get('source') == 'local' and file_item.get('webContentLink'):
            self.open_drive_button.setVisible(True)
        else:
            self.open_drive_button.setVisible(False)

        self.thumbnail_label.setPixmap(ThumbnailManager.get_generic_thumbnail(
            file_item.get('mimeType'), size=(400, 400)))

        mime = file_item.get('mimeType', '')
        local_path = file_item.get('path')

        try:
            if ThumbnailCache.is_thumbnail_cached(file_item):
                cached = ThumbnailCache.get_existing_thumbnail_cache_path(
                    file_item)
                pixmap = QPixmap(cached)
                if not pixmap.isNull():
                    self.thumbnail_label.setPixmap(pixmap.scaled(
                        self.thumbnail_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                    self.show()
                    return
        except Exception:
            pass

        if local_path and os.path.exists(local_path) and mime.startswith('image/'):
            try:
                if ThumbnailCache.is_thumbnail_cached(file_item):
                    cached = ThumbnailCache.get_existing_thumbnail_cache_path(
                        file_item)
                    pixmap = QPixmap(cached)
                    if not pixmap.isNull():
                        self.thumbnail_label.setPixmap(pixmap.scaled(
                            self.thumbnail_label.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        ))
                        self.show()
                else:
                    pass
            except Exception:
                pass
        elif local_path and os.path.exists(local_path):
            self.thumbnail_label.setPixmap(
                ThumbnailManager.get_generic_thumbnail(mime, size=(400, 400)))
            self.show()
        else:
            self.show()

        if file_item.get('source') == 'local' and file_item.get('path') and os.path.exists(file_item.get('path')):
            self.open_folder_button.setVisible(True)
        else:
            self.open_folder_button.setVisible(False)

    def open_folder(self):
        file_path = self.current_file_item.get('path')
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Arquivo não encontrado",
                                "O caminho do arquivo não existe.")
            return
        folder = os.path.dirname(file_path)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            QMessageBox.critical(self, "Erro ao abrir pasta",
                                 f"Não foi possível abrir a pasta: {e}")
        self.show()

    def open_drive_link(self):
        drive_link = self.current_file_item.get('webContentLink')
        if not drive_link:
            QMessageBox.warning(self, "Link não disponível",
                                "O link do Google Drive não está disponível.")
            return
        try:
            webbrowser.open(drive_link)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao abrir link",
                                 f"Não foi possível abrir o link: {e}")
        self.show()

    def on_thumbnail_loaded(self, image_data, thumbnail_path):

        if image_data and thumbnail_path:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                self.thumbnail_label.setPixmap(pixmap.scaled(
                    self.thumbnail_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                try:
                    indexer = getattr(self.parent_app, 'indexer', None)
                    if indexer:
                        indexer.update_thumbnail_path(
                            self.current_file_item.get('id'), thumbnail_path
                        )
                except Exception:
                    pass
            else:
                self.thumbnail_label.setPixmap(ThumbnailManager.get_generic_thumbnail(
                    self.current_file_item.get('mimeType'), size=(96, 96)))
        else:
            self.thumbnail_label.setPixmap(ThumbnailManager.get_generic_thumbnail(
                self.current_file_item.get('mimeType'), size=(96, 96)))

        if self.thumbnail_worker and self.thumbnail_thread:
            self.thumbnail_thread.quit()
            self.thumbnail_thread.wait()
            self.thumbnail_worker.deleteLater()
            self.thumbnail_thread.deleteLater()
            self.thumbnail_worker = None
            self.thumbnail_thread = None
