# Visualizador de lista de arquivos personalizado com menu de contexto e funcionalidade de arrastar e soltar.

import os
from PyQt6.QtWidgets import QListView, QMenu, QApplication
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import QDrag, QCursor
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDrag


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
        copy_action = menu.addAction("Copiar Caminho")

        action = menu.exec(self.viewport().mapToGlobal(position))
        if action == open_action:
            if file_item.get('source') == 'local' and file_item.get('path'):
                folder = os.path.dirname(file_item['path'])
                os.startfile(folder)
        elif action == copy_action:
            caminho = file_item.get('path') or file_item.get('webViewLink')
            if caminho:
                if file_item.get('source') == 'local' and file_item.get('path'):
                    caminho = os.path.normpath(caminho)
                QApplication.clipboard().setText(caminho)
