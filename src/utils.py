# utils.py - Funções utilitárias do Vox Imago
# Inclui funções para configurações, thumbnails e formatação de tamanho de arquivos.
# Use este arquivo para importar utilitários em todo o projeto.

import os
import json
import hashlib
import mimetypes
import requests
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QImage
from PyQt6.QtCore import Qt

from .database import normalize_text

THUMBNAIL_CACHE_DIR = 'assets/thumbnail_cache'

SETTINGS_FILE = 'config/settings.json'


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)


def get_generic_thumbnail(mime_type, size=(48, 48)):
    icon_dir = os.path.join(os.path.dirname(
        os.path.dirname(__file__)), "assets", "icons")
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
        if size_in_bytes < 1024:
            return f"{size_in_bytes} B"
        elif size_in_bytes < 1024**2:
            return f"{size_in_bytes / 1024:.2f} KB"
        elif size_in_bytes < 1024**3:
            return f"{size_in_bytes / 1024**2:.2f} MB"
        else:
            return f"{size_in_bytes / 1024**3:.2f} GB"
        return f"{size_in_bytes / 1024**3:.2f} GB"


def get_thumbnail_cache_key(file_item):
    if file_item.get('source') == 'local':
        path = file_item.get('path', '')
        mtime = str(file_item.get('modifiedTime', ''))
        size = str(file_item.get('size', ''))
        key = hashlib.sha1(f"{path}|{mtime}|{size}".encode()).hexdigest()
    else:
        file_id = file_item.get('id', '')
        modified_time = str(file_item.get('modifiedTime', ''))
        key = hashlib.sha1(f"{file_id}|{modified_time}".encode()).hexdigest()
    return key


def ensure_thumbnail_cache_dir():
    try:
        if not os.path.exists(THUMBNAIL_CACHE_DIR):
            os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)
    except Exception as e:
        print(f"❌ Erro criando diretório de cache: {e}")
        pass
    return THUMBNAIL_CACHE_DIR


def get_thumbnail_cache_path(file_item, ext='png'):
    ensure_thumbnail_cache_dir()
    key = get_thumbnail_cache_key(file_item)
    return os.path.join(THUMBNAIL_CACHE_DIR, f"{key}.{ext}")


def is_thumbnail_cached(file_item):
    path_jpg = get_thumbnail_cache_path(file_item, 'jpg')
    path_png = get_thumbnail_cache_path(file_item, 'png')
    hit = False
    if os.path.exists(path_png):
        hit = True
    if os.path.exists(path_jpg):
        hit = True
    return hit


def get_existing_thumbnail_cache_path(file_item):
    path_png = get_thumbnail_cache_path(file_item, 'png')
    path_jpg = get_thumbnail_cache_path(file_item, 'jpg')
    if os.path.exists(path_png):
        return path_png
    if os.path.exists(path_jpg):
        return path_jpg
    return path_png


def generate_local_image_thumbnail(file_item, base_size=256):
    try:
        if not file_item:
            return None
        mime = (file_item.get('mimeType') or '').lower()
        local_path = file_item.get('path')
        if not local_path or not os.path.exists(local_path):
            return None
        if not mime.startswith('image/'):
            guessed, _ = mimetypes.guess_type(local_path)
            if not guessed or not guessed.startswith('image/'):
                return None

        img = QImage(local_path)
        if img.isNull():
            return None
        img = img.scaled(base_size, base_size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
        cache_path = get_thumbnail_cache_path(file_item, 'png')
        ensure_thumbnail_cache_dir()
        ok = img.save(cache_path, 'PNG')
        if not ok:
            return None
        return cache_path
    except Exception as e:
        return None


def generate_drive_thumbnail(file_item, base_size=256):
    try:
        if not file_item or file_item.get('source') != 'drive':
            return None
        url = file_item.get('thumbnailLink') or file_item.get('thumbnail_link')
        if not url:
            return None
        ensure_thumbnail_cache_dir()
        tmp_path = get_thumbnail_cache_path(file_item, 'png')
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200 or not resp.content:
            return None
        img = QImage()
        if not img.loadFromData(resp.content):
            return None
        img = img.scaled(base_size, base_size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
        ok = img.save(tmp_path, 'PNG')
        if not ok:
            return None
        return tmp_path
    except Exception as e:
        return None


def generate_local_pdf_thumbnail(file_item, base_size=256):
    try:
        local_path = file_item.get('path')
        if not local_path or not os.path.exists(local_path):
            return None
        _, ext = os.path.splitext(local_path)
        if (file_item.get('mimeType') or '').lower() != 'application/pdf' and ext.lower() != '.pdf':
            return None
        try:
            import fitz
        except Exception:
            return None
        doc = fitz.open(local_path)
        if doc.page_count == 0:
            return None
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        cache_path = get_thumbnail_cache_path(file_item, 'png')
        ensure_thumbnail_cache_dir()
        pix.save(cache_path)
        img = QImage(cache_path)
        if img.isNull():
            return cache_path
        img = img.scaled(base_size, base_size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
        img.save(cache_path, 'PNG')
        return cache_path
    except Exception as e:
        return None


def generate_local_video_thumbnail(file_item, base_size=256):
    try:
        local_path = file_item.get('path')
        if not local_path or not os.path.exists(local_path):
            return None
        mime = (file_item.get('mimeType') or '').lower()
        guessed, _ = mimetypes.guess_type(local_path)
        is_video = (mime.startswith('video/')
                    or (guessed and guessed.startswith('video/')))
        video_exts = {'.mp4', '.mov', '.avi',
                      '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        if not is_video and os.path.splitext(local_path)[1].lower() not in video_exts:
            return None
        try:
            os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = '-loglevel quiet'
            import cv2
            import numpy as np
            cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
        except Exception:
            return None
        cap = cv2.VideoCapture(local_path)
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_MSEC, 500)
            ret, frame = cap.read()
            if not ret:
                cap.release()
                return None
        cap.release()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        img = QImage(frame_rgb.data, w, h, bytes_per_line,
                     QImage.Format.Format_RGB888).copy()
        img = img.scaled(base_size, base_size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
        cache_path = get_thumbnail_cache_path(file_item, 'png')
        ensure_thumbnail_cache_dir()
        ok = img.save(cache_path, 'PNG')
        return cache_path if ok else None
    except Exception as e:
        return None


def generate_local_thumbnail(file_item, base_size=256):
    path = generate_local_image_thumbnail(file_item, base_size=base_size)
    if path:
        return path
    path = generate_local_pdf_thumbnail(file_item, base_size=base_size)
    if path:
        return path
    path = generate_local_video_thumbnail(file_item, base_size=base_size)
    if path:
        return path
    return None


def find_local_matches(drive_file, local_files_cursor):

    matches = []
    drive_name = drive_file.get('name', '')
    drive_size = drive_file.get('size', 0)

    print(f"🔍 Procurando matches para: '{drive_name}' (tamanho: {drive_size})")

    local_files_cursor.execute(
        "SELECT file_id FROM files WHERE source='local' AND LOWER(name)=LOWER(?) AND size=?",
        (drive_name, drive_size)
    )
    exact_matches = local_files_cursor.fetchall()
    for match in exact_matches:
        matches.append(match[0])
        print(f"✅ Match EXATO encontrado: ID {match[0]}")

    if len(matches) == 0:
        drive_name_normalized = normalize_text(drive_name)
        print(
            f"🔍 Tentando busca normalizada: '{drive_name}' → '{drive_name_normalized}'")

        local_files_cursor.execute(
            "SELECT file_id, name FROM files WHERE source='local' AND size=?",
            (drive_size,)
        )
        candidates = local_files_cursor.fetchall()

        for file_id, local_name in candidates:
            local_name_normalized = normalize_text(local_name)
            if local_name_normalized.lower() == drive_name_normalized.lower():
                matches.append(file_id)
                print(
                    f"✅ Match NORMALIZADO encontrado: '{local_name}' → '{local_name_normalized}' (ID: {file_id})")

    return matches
