# file_list_model.py - Modelo de dados para lista de arquivos do Vox Imago
# Gerencia e exibe listas de arquivos na interface principal.

from PyQt6.QtCore import Qt, QAbstractListModel, QModelIndex, QVariant


class FileListModel(QAbstractListModel):
    def __init__(self, files=None):
        super().__init__()
        self._files = files or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._files)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._files)):
            return QVariant()
        file_item = self._files[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return file_item.get('name', '')
        if role == Qt.ItemDataRole.UserRole:
            return file_item
        return QVariant()

    def setFiles(self, files):
        self.beginResetModel()
        self._files = files
        self.endResetModel()

    def addFiles(self, files):
        if not files:
            return
        self.beginInsertRows(QModelIndex(), len(
            self._files), len(self._files) + len(files) - 1)
        self._files.extend(files)
        self.endInsertRows()
