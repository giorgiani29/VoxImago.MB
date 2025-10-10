# file_list_delegate.py - Delegado personalizado para renderização da lista de arquivos
# Exibe itens com miniaturas, nomes e metadados na interface principal.

import os
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QApplication, QStyle
from PyQt6.QtGui import QPixmap, QFont, QPalette
from PyQt6.QtCore import Qt, QModelIndex, QSize, QEvent, QRect, pyqtSignal, QObject
from .utils import get_generic_thumbnail, format_size, is_thumbnail_cached, get_thumbnail_cache_path, get_existing_thumbnail_cache_path


class FileListDelegate(QStyledItemDelegate):
    requestThumbnail = pyqtSignal(dict)

    def __init__(self, parent=None, indexer=None):
        super().__init__(parent)
        self.indexer = indexer

    def paint(self, painter, option, index):
        file_item = index.data(Qt.ItemDataRole.UserRole)
        if not file_item:
            return super().paint(painter, option, index)

        painter.save()
        rect = option.rect
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, option.palette.highlight())
        else:
            painter.fillRect(rect, option.palette.base())

        pixmap = None
        if file_item.get('source') == 'local' or file_item.get('source') == 'drive':
            if is_thumbnail_cached(file_item):
                cached = get_existing_thumbnail_cache_path(file_item)
                p = QPixmap(cached)
                if not p.isNull():
                    pixmap = p
            else:
                try:
                    self.requestThumbnail.emit(file_item)
                except Exception:
                    pass
        if pixmap is None:
            pixmap = get_generic_thumbnail(file_item.get('mimeType'))
        if pixmap:
            pixmap = pixmap.scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(rect.left()+8, rect.top()+6, pixmap)

        name = file_item.get('name', 'Nome Desconhecido')
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.setPen(option.palette.text().color())
        painter.drawText(rect.left()+64, rect.top()+22, name)

        source = file_item.get('source', 'local')
        if source == 'drive':
            local_path = file_item.get('path')
            if local_path and os.path.exists(local_path):
                source_name = "Cloud (Local)"
            else:
                source_name = "Cloud"
        else:
            source_name = "Local"

        painter.setFont(QFont("Arial", 8))
        painter.setPen(Qt.GlobalColor.gray)
        painter.drawText(rect.left()+64, rect.top()+38, f"({source_name})")

        painter.restore()

    def editorEvent(self, event, model, option, index):
        return super().editorEvent(event, model, option, index)

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 60)
