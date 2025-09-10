# widgets.py - Componentes visuais customizados do Vox Imago
# Inclui FileItemWidget, DownloadProgressDialog, OptionsDialog, ClickableLabel
# Use este arquivo para importar widgets personalizados na interface principal.

import os
import sys
import sqlite3
import webbrowser
import cv2
import platform

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar, QPushButton, QDialog, QFrame, QMessageBox, QApplication, QDialogButtonBox, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QMimeData, QUrl, QTime, QThreadPool, QRunnable, QObject
from PyQt6.QtGui import QPixmap, QFont, QPalette, QDrag, QImage


from utils import get_generic_thumbnail, format_size

from workers import DownloadWorker, ThumbnailWorker
from utils import load_settings, get_thumbnail_cache_key

THUMBNAIL_CACHE_DIR = "thumbnail_cache"


class FileItemWidget(QFrame):
    selected = pyqtSignal(object)
    folder_clicked = pyqtSignal(str)

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

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(48, 48)
        self.name_label = QLabel(
            self.file_item.get('name', 'Nome Desconhecido'))
        self.name_label.setFont(QFont("Arial", 10))
        self.name_label.setWordWrap(False)

        source_name = "Local" if self.file_item.get(
            'source') == 'local' else "Drive"
        self.source_label = QLabel(f"({source_name})")
        self.source_label.setFont(QFont("Arial", 8))
        self.source_label.setStyleSheet("color: gray;")

        self.apply_theme_style()

        self.main_layout.addWidget(self.thumbnail_label)
        self.main_layout.addSpacing(15)

        name_source_layout = QVBoxLayout()
        name_source_layout.addWidget(self.name_label)
        name_source_layout.addWidget(self.source_label)
        name_source_layout.setSpacing(0)

        self.main_layout.addLayout(name_source_layout, 1)
        self.main_layout.addStretch()
        self.main_layout.setContentsMargins(10, 5, 10, 5)

        self.download_in_progress = False
        self.local_file_path = self.file_item.get('path')

        self.download_thread = None
        self.download_worker = None
        self.thumbnail_thread = None
        self.thumbnail_worker = None
        self.download_dialog = None

        self.star_button = QPushButton(
            "★" if parent_app.indexer.is_starred(file_item.get('id')) else "☆")
        self.star_button.setFixedWidth(30)
        self.star_button.setStyleSheet(
            "font-size: 18px; border: none; background: transparent;")
        self.star_button.clicked.connect(self.toggle_starred)
        self.main_layout.addWidget(self.star_button)


    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, "thumbnail_loaded") or not self.thumbnail_loaded:
            self.load_thumbnail()
            self.thumbnail_loaded = True

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

    def set_thumbnail(self, pixmap):
        pixmap_scaled = pixmap.scaled(
            self.thumbnail_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.thumbnail_label.setPixmap(pixmap_scaled)

    def load_thumbnail(self):
        from database import THUMBNAIL_CACHE_DIR
        from utils import get_thumbnail_cache_key
        import os
        cache_key = get_thumbnail_cache_key(self.file_item)
        thumbnail_path = os.path.join(THUMBNAIL_CACHE_DIR, f"{cache_key}.jpg")
        os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)
        if os.path.exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            self.thumbnail_label.setPixmap(pixmap)
            self.thumbnail_loaded = True
            return
        if self.file_item.get('source') == 'drive' and self.file_item.get('thumbnailLink'):
            self.thumbnail_thread = QThread()
            self.thumbnail_worker = ThumbnailWorker(
                self.file_item.get('thumbnailLink'), self.file_item)
            self.thumbnail_worker.moveToThread(self.thumbnail_thread)
            self.thumbnail_thread.started.connect(self.thumbnail_worker.run)
            self.thumbnail_worker.finished.connect(self.on_thumbnail_loaded)
            self.thumbnail_thread.start()
        else:
            self.thumbnail_label.setPixmap(
                get_generic_thumbnail(self.file_item.get('mimeType')))
            self.thumbnail_loaded = True

    def get_video_thumbnail(self, video_path):
        try:
            cap = cv2.VideoCapture(video_path)
            success, frame = cap.read()
            cap.release()
            if success and frame is not None:
                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                image = QImage(frame.data, width, height, bytes_per_line,
                               QImage.Format.Format_RGB888).rgbSwapped()
                pixmap = QPixmap.fromImage(image)
                return pixmap
        except Exception as e:
            print(f"Erro ao gerar thumbnail de vídeo: {e}")
        return QPixmap()

    def on_thumbnail_loaded(self, image_data, thumbnail_path):
        if self.thumbnail_worker and self.thumbnail_thread:
            self.thumbnail_thread.quit()
            self.thumbnail_thread.wait()
            self.thumbnail_worker.deleteLater()
            self.thumbnail_thread.deleteLater()
            self.thumbnail_worker = None
            self.thumbnail_thread = None
            self.thumbnail_loaded = True

        if image_data and thumbnail_path:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                self.set_thumbnail(pixmap)
                conn = sqlite3.connect('file_index.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE files SET thumbnailPath = ? WHERE file_id = ?",
                               (thumbnail_path, self.file_item.get('id')))
                conn.commit()
                conn.close()
            else:
                self.set_thumbnail(get_generic_thumbnail(
                    self.file_item.get('mimeType')))
        else:
            self.set_thumbnail(get_generic_thumbnail(
                self.file_item.get('mimeType')))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.file_item.get('mimeType') == 'application/vnd.google-apps.folder' or self.file_item.get('mimeType') == 'folder':
                self.folder_clicked.emit(self.file_item.get('id'))
            else:
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
                self.open_file()

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
        else:
            self.download_thread = QThread()
            self.download_worker = DownloadWorker(self.service, self.file_item)
            self.download_worker.moveToThread(self.download_thread)

            self.download_worker.download_started.connect(
                lambda name, size: self.status_bar_callback(f"Baixando {name}..."))
            self.download_worker.download_finished.connect(
                self.on_download_finished_and_open)
            self.download_worker.download_failed.connect(
                lambda error: QMessageBox.critical(self, "Erro de Download", error))

            self.download_thread.started.connect(self.download_worker.run)
            self.download_thread.start()

    def on_download_finished_and_open(self, file_path, file_name):
        QMessageBox.information(
            self, "Download Concluído", f"O arquivo '{file_name}' foi baixado com sucesso.")
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            else:
                webbrowser.open_new_tab(f'file:///{file_path}')
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Abrir Arquivo",
                                 f"Não foi possível abrir o arquivo: {e}")

        if self.download_thread and self.download_worker:
            self.download_thread.quit()
            self.download_thread.wait()
            self.download_worker.deleteLater()
            self.download_thread.deleteLater()
            self.download_thread = None
            self.download_worker = None

    def start_drag_download_if_needed(self):
        if self.file_item.get('source') == 'local' or (self.local_file_path and os.path.exists(self.local_file_path)):
            self.do_drag()
            return

        if self.download_in_progress:
            self.status_bar_callback("Download já em andamento.")
            return

        self.start_download()

    def start_download(self):
        if self.download_in_progress:
            return

        self.download_in_progress = True

        self.download_thread = QThread()
        self.download_worker = DownloadWorker(self.service, self.file_item)
        self.download_worker.moveToThread(self.download_thread)

        self.download_worker.download_started.connect(self.on_download_started)
        self.download_worker.download_progress.connect(
            self.on_download_progress)
        self.download_worker.download_finished.connect(
            self.on_download_finished)
        self.download_worker.download_failed.connect(self.on_download_failed)

        self.download_thread.started.connect(self.download_worker.run)
        self.download_thread.start()

    def on_download_started(self, file_name, file_size):
        if file_size > 5 * 1024 * 1024:
            self.download_dialog = DownloadProgressDialog(
                file_name, self.parent_app)
            self.download_dialog.show()
        else:
            self.status_bar_callback(f"Baixando {file_name}...")

    def on_download_progress(self, downloaded_bytes, total_bytes):
        if self.download_dialog:
            self.download_dialog.update_progress(downloaded_bytes, total_bytes)

    def do_drag(self):
        if self.file_item.get('source') == 'local' or (self.local_file_path and os.path.exists(self.local_file_path)):
            drag = QDrag(self)
            mime_data = QMimeData()
            urls = [QUrl.fromLocalFile(self.local_file_path)]
            mime_data.setUrls(urls)
            drag.setMimeData(mime_data)

            pixmap = self.thumbnail_label.pixmap()
            if pixmap:
                drag.setPixmap(pixmap)
                drag.setHotSpot(self.thumbnail_label.rect().center())

            drag.exec(Qt.DropAction.CopyAction)
            return

        mime_type = self.file_item.get('mimeType')
        file_size = self.file_item.get('size', 0)
        is_small_file = file_size < 5 * 1024 * 1024

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.file_item.get('name'))
        drag.setMimeData(mime_data)

        pixmap = self.thumbnail_label.pixmap()
        if pixmap:
            drag.setPixmap(pixmap)
            drag.setHotSpot(self.thumbnail_label.rect().center())

        drag.exec(Qt.DropAction.CopyAction)

        if is_small_file:
            if not self.download_in_progress:
                self.start_download()
            else:
                self.status_bar_callback("Download já em andamento.")
        else:
            self.status_bar_callback(
                "Arraste arquivos grandes apenas após baixá-los pelo botão de download.")

    def on_download_finished(self, file_path, file_name):
        self.download_in_progress = False
        self.local_file_path = file_path
        self.status_bar_callback(f"Download de {file_name} concluído.")

        conn = sqlite3.connect('file_index.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE files SET path = ? WHERE file_id = ?",
                       (file_path, self.file_item.get('id')))
        conn.commit()
        conn.close()

        if self.download_dialog:
            self.download_dialog.accept()
            self.download_dialog = None

        self.status_bar_callback(
            f"Download de {file_name} concluído. Agora você pode arrastá-lo para qualquer lugar.")

        if self.download_thread and self.download_worker:
            self.download_thread.quit()
            self.download_thread.wait()
            self.download_thread.deleteLater()
            self.download_worker.deleteLater()
            self.download_thread = None
            self.download_worker = None

    def on_download_failed(self, error_message):
        self.download_in_progress = False

        if self.download_dialog:
            self.download_dialog.reject()
            self.download_dialog = None

        QMessageBox.critical(self, "Erro no Download", error_message)
        self.status_bar_callback("Download falhou.")

        if self.download_thread and self.download_worker:
            self.download_thread.quit()
            self.download_thread.wait()
            self.download_thread.deleteLater()
            self.download_worker.deleteLater()
            self.download_thread = None
            self.download_worker = None

    def cleanup(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.quit()
            self.download_thread.wait()
        if self.thumbnail_thread and self.thumbnail_thread.isRunning():
            self.thumbnail_thread.quit()
            self.thumbnail_thread.wait()


class DownloadProgressDialog(QDialog):
    def __init__(self, file_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Baixando Arquivo...")
        self.setModal(True)
        self.setFixedSize(400, 150)

        self.start_time = QTime.currentTime()
        self.last_update_time = self.start_time
        self.last_update_bytes = 0
        self.total_bytes = 0
        self.current_bytes = 0

        main_layout = QVBoxLayout(self)

        self.file_label = QLabel(f"Baixando: {file_name}")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.file_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Conectando...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.estimated_time_label = QLabel("Tempo estimado: Calculando...")
        self.estimated_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.estimated_time_label)

    def update_progress(self, downloaded_bytes, total_bytes):
        self.current_bytes = downloaded_bytes
        self.total_bytes = total_bytes

        if total_bytes > 0:
            percentage = int((downloaded_bytes / total_bytes) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(
                f"{percentage}% - {format_size(downloaded_bytes)} de {format_size(total_bytes)}")

            self.update_estimated_time()
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Conectando...")

    def update_estimated_time(self):
        current_time = QTime.currentTime()
        elapsed_ms = self.start_time.msecsTo(current_time)

        if elapsed_ms > 1000 and self.current_bytes > 0:
            speed = self.current_bytes / (elapsed_ms / 1000)
            remaining_bytes = self.total_bytes - self.current_bytes
            if speed > 0:
                remaining_seconds = remaining_bytes / speed
                if remaining_seconds < 60:
                    time_str = f"{int(remaining_seconds)} seg"
                elif remaining_seconds < 3600:
                    minutes = int(remaining_seconds / 60)
                    seconds = int(remaining_seconds % 60)
                    time_str = f"{minutes} min {seconds} seg"
                else:
                    hours = int(remaining_seconds / 3600)
                    minutes = int((remaining_seconds % 3600) / 60)
                    time_str = f"{hours}h {minutes}min"
                self.estimated_time_label.setText(
                    f"Tempo estimado: {time_str}")
                self.status_label.setText("Baixando...")
            else:
                self.estimated_time_label.setText(
                    "Tempo estimado: Calculando...")


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

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.main_layout.addWidget(self.button_box)

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
