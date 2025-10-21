# file_list_delegate.py - Delegado personalizado para renderização da lista de arquivos
# Exibe itens com miniaturas, nomes e metadados na interface principal.

import os
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtCore import QRect
from .utils import get_generic_thumbnail, is_thumbnail_cached, get_existing_thumbnail_cache_path


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

        parent_view = self.parent()
        is_grid = hasattr(parent_view, 'viewMode') and parent_view.viewMode(
        ) == parent_view.ViewMode.IconMode

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

        if is_grid:
            icon_size = parent_view.iconSize().width()
            pixmap = pixmap.scaled(
                icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x_icon = rect.left() + (rect.width() - icon_size) // 2
            y_icon = rect.top() + 12
            painter.drawPixmap(x_icon, y_icon, pixmap)

            name = file_item.get('name', 'Nome Desconhecido')
            max_name_width = rect.width() - 16
            font = QFont("Arial", 10, QFont.Weight.Bold)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            elided_name = metrics.elidedText(
                name, Qt.TextElideMode.ElideRight, max_name_width)
            name_height = metrics.height()
            name_bg_rect = QRect(
                rect.left()+8, rect.bottom() - name_height-12, rect.width()-16, name_height+6)
            painter.setBrush(Qt.GlobalColor.black)
            painter.setOpacity(0.45)
            painter.setPen(Qt.GlobalColor.transparent)
            painter.drawRect(name_bg_rect)
            painter.setOpacity(1.0)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(
                name_bg_rect, Qt.AlignmentFlag.AlignCenter, elided_name)

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
            painter.drawText(rect.left()+8, rect.bottom()-6, source_name)
        else:
            icon_size = 48
            pixmap = pixmap.scaled(
                icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x_icon = rect.left() + 8
            y_icon = rect.top() + (rect.height() - icon_size) // 2
            painter.drawPixmap(x_icon, y_icon, pixmap)

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
        parent_view = self.parent()
        if hasattr(parent_view, 'viewMode') and parent_view.viewMode() == parent_view.ViewMode.IconMode:
            grid_size = parent_view.gridSize()
            return grid_size
        return QSize(option.rect.width(), 60)
 