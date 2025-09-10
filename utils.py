# utils.py - Funções utilitárias do Vox Imago
# Inclui funções para configurações, thumbnails e formatação de tamanho de arquivos.
# Use este arquivo para importar utilitários em todo o projeto.

import os
import json
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor
from PyQt6.QtCore import Qt

SETTINGS_FILE = 'settings.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def get_generic_thumbnail(mime_type, size=(48, 48)):
    icon_dir = os.path.join(os.path.dirname(__file__), "icons")
    icon_map = {
        'folder': 'folder.png',
        'application/vnd.google-apps.folder': 'folder.png',
        'application/pdf': 'pdf.png',
        'application/vnd.google-apps.document': 'doc.png',
        'application/msword': 'doc.png',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'doc.png',
        'application/vnd.google-apps.spreadsheet': 'xls.png',
        'application/vnd.ms-excel': 'xls.png',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xls.png',
        'application/vnd.google-apps.presentation': 'ppt.png',
        'application/vnd.ms-powerpoint': 'ppt.png',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'ppt.png',
    }
    if mime_type.startswith('image/'):
        icon_file = 'image.png'
    else:
        icon_file = icon_map.get(mime_type, 'file.png')

    icon_path = os.path.join(icon_dir, icon_file)
    if os.path.exists(icon_path):
        pixmap = QPixmap(icon_path)
        return pixmap.scaled(size[0], size[1], Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    else:
        pixmap = QPixmap(size[0], size[1])
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.drawRect(0, 0, size[0], size[1])
        painter.end()
        return pixmap

def format_size(size_in_bytes):
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024**2:
        return f"{size_in_bytes / 1024:.2f} KB"
    elif size_in_bytes < 1024**3:
        return f"{size_in_bytes / 1024**2:.2f} MB"
    else:
        return f"{size_in_bytes / 1024**3:.2f} GB"
    
    
def load_settings():

    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):

    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def get_generic_thumbnail(mime_type, size=(48, 48)):
    """
    Carrega ícones reais para tipos de arquivo, simulando ícones do Windows.
    """
    icon_dir = os.path.join(os.path.dirname(__file__), "icons")
    icon_map = {
        'folder': 'folder.png',
        'application/vnd.google-apps.folder': 'folder.png',
        'application/pdf': 'pdf.png',
        'application/vnd.google-apps.document': 'doc.png',
        'application/msword': 'doc.png',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'doc.png',
        'application/vnd.google-apps.spreadsheet': 'xls.png',
        'application/vnd.ms-excel': 'xls.png',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xls.png',
        'application/vnd.google-apps.presentation': 'ppt.png',
        'application/vnd.ms-powerpoint': 'ppt.png',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'ppt.png',
    }
    if mime_type.startswith('image/'):
        icon_file = 'image.png'
    else:
        icon_file = icon_map.get(mime_type, 'file.png')

    icon_path = os.path.join(icon_dir, icon_file)
    if os.path.exists(icon_path):
        pixmap = QPixmap(icon_path)
        return pixmap.scaled(size[0], size[1], Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    else:

        pixmap = QPixmap(size[0], size[1])
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.drawRect(0, 0, size[0], size[1])
        painter.end()
        return pixmap

def format_size(size_in_bytes):

    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024**2:
        return f"{size_in_bytes / 1024:.2f} KB"
    elif size_in_bytes < 1024**3:
        return f"{size_in_bytes / 1024**2:.2f} MB"
    else:
        return f"{size_in_bytes / 1024**3:.2f} GB"
