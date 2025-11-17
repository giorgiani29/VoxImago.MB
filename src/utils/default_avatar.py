from PyQt6.QtGui import QPixmap, QColor, QPainter
from PyQt6.QtCore import Qt

def create_default_avatar(size=64):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(180, 180, 180))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.setBrush(QColor(220, 220, 220))
    painter.drawEllipse(size//4, size//4, size//2, size//2)
    painter.end()
    return pixmap
