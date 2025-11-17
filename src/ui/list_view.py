'''
Visualizador de lista de arquivos personalizado com menu de contexto e funcionalidade de arrastar e soltar.
'''

import os
from PyQt6.QtWidgets import QListView, QMenu, QApplication, QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QUrl
from PyQt6.QtGui import QDrag, QCursor, QPixmap, QImage
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PIL import Image
try:
    import rawpy
except ImportError:
    rawpy = None


class FileListView(QListView):
    fileSelected = pyqtSignal(object)
    fileDoubleClicked = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.drag_start_position = None
        self.doubleClicked.connect(self._emit_double_click)

    def setModel(self, model):
        super().setModel(model)
        if self.selectionModel():
            self.selectionModel().selectionChanged.connect(self._emit_selection)

    def _emit_selection(self, selected, deselected):
        indexes = self.selectedIndexes()
        if indexes:
            file_item = indexes[0].data(Qt.ItemDataRole.UserRole)
            self.fileSelected.emit(file_item)

    def _emit_double_click(self, index):
        file_item = index.data(Qt.ItemDataRole.UserRole)
        self.fileDoubleClicked.emit(file_item)

    def mousePressEvent(self, event):
        self.drag_start_position = event.pos()
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                self.setCurrentIndex(index)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start_position is not None and (event.pos() - self.drag_start_position).manhattanLength() > QApplication.startDragDistance():
            self.startDrag(Qt.DropAction.CopyAction)
            self.drag_start_position = None
        super().mouseMoveEvent(event)

    def startDrag(self, supportedActions):
        indexes = self.selectedIndexes()
        if not indexes:
            index = self.indexAt(self.mapFromGlobal(QCursor.pos()))
            if index.isValid():
                self.setCurrentIndex(index)
        indexes = self.selectedIndexes()
        if not indexes:
            return

        mime_data = QMimeData()
        urls = []
        for index in indexes:
            file_item = index.data(Qt.ItemDataRole.UserRole)
            if file_item.get('source') == 'local' and file_item.get('path'):
                urls.append(QUrl.fromLocalFile(file_item['path']))
            elif file_item.get('source') == 'drive' and file_item.get('webViewLink'):
                urls.append(QUrl(file_item['webViewLink']))
        mime_data.setUrls(urls)

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)

    def show_context_menu(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return

        file_item = index.data(Qt.ItemDataRole.UserRole)
        menu = QMenu()

        open_action = menu.addAction("Abrir no Explorer")
        copy_pt_action = menu.addAction("Copiar Caminho em Português")
        copy_en_action = menu.addAction("Copiar Caminho em Inglês")

        action = menu.exec(self.viewport().mapToGlobal(position))
        if action == open_action:
            if file_item.get('source') == 'local' and file_item.get('path'):
                folder = os.path.dirname(file_item['path'])
                os.startfile(folder)
        elif action == copy_pt_action or action == copy_en_action:
            caminho = file_item.get('path') or file_item.get('webViewLink')
            if caminho:
                if file_item.get('source') == 'local' and file_item.get('path'):
                    caminho = os.path.normpath(caminho)
                if action == copy_pt_action:
                    caminho = caminho.replace(
                        'Shared drives', 'Drives compartilhados')
                elif action == copy_en_action:
                    caminho = caminho.replace(
                        'Drives compartilhados', 'Shared drives')
                QApplication.clipboard().setText(caminho)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.show_quick_preview()
        else:
            super().keyPressEvent(event)

    def show_quick_preview(self):
        indexes = self.selectedIndexes()
        if not indexes:
            return
        file_item = indexes[0].data(Qt.ItemDataRole.UserRole)
        file_path = file_item.get('path')
        if not file_path or not os.path.exists(file_path):
            return

        ext = os.path.splitext(file_path)[1].lower()
        video_exts = {'.mp4', '.avi', '.mov',
                      '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        raw_exts = {'.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2',
                    '.pef', '.srw', '.raf', '.raw', '.heic', '.heif'}

        dialog = QDialog(self)
        dialog.setWindowTitle("Pré-visualização")
        layout = QVBoxLayout(dialog)

        if ext in video_exts:
            try:
                video_widget = QVideoWidget(dialog)
                layout.addWidget(video_widget)
                player = QMediaPlayer(dialog)
                audio = QAudioOutput(dialog)
                player.setAudioOutput(audio)
                player.setVideoOutput(video_widget)
                player.setSource(QUrl.fromLocalFile(file_path))
                player.play()
                dialog.resize(900, 600)

                def stop_player():
                    player.stop()
                dialog.finished.connect(stop_player)

            except Exception as e:
                label = QLabel(f"Erro ao tentar exibir vídeo: {e}", dialog)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(label)
        elif ext in raw_exts:
            try:
                if rawpy:
                    with rawpy.imread(file_path) as raw:
                        rgb = raw.postprocess()
                        image = Image.fromarray(rgb)
                else:
                    image = Image.open(file_path)
                image = image.convert("RGB")
                image.thumbnail((800, 600))
                data = image.tobytes("raw", "RGB")
                qimage = QImage(data, image.width, image.height,
                                QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)
                label = QLabel(dialog)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setPixmap(pixmap)
                layout.addWidget(label)
            except Exception as e:
                label = QLabel(f"Não foi possível exibir RAW: {e}", dialog)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(label)
            dialog.resize(820, 620)
        else:
            label = QLabel(dialog)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                label.setPixmap(pixmap.scaled(
                    800, 600, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                label.setText("Não foi possível carregar a imagem.")
            layout.addWidget(label)
            dialog.resize(820, 620)

        dialog.setLayout(layout)
        dialog.setModal(True)

        def close_on_key(event):
            if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Escape):
                dialog.close()
            else:
                QDialog.keyPressEvent(dialog, event)
        dialog.keyPressEvent = close_on_key

        dialog.exec()
