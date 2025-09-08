# coding=utf-8
import sys
import os
import requests
import io
import webbrowser
import platform
import mimetypes
import sqlite3
import json
import time
import re
import datetime
import uuid
import cv2

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QMessageBox, QFrame, QSizePolicy, QSpacerItem, QFileDialog,
    QDialog, QCheckBox, QDialogButtonBox, QProgressBar, QComboBox, QCompleter,
    QFormLayout, QSplitter, QDateEdit
)
from PyQt6.QtGui import QPixmap, QImage, QDrag, QPainter, QFont, QPen, QColor, QBrush, QPolygon, QPalette
from PyQt6.QtCore import Qt, QMimeData, QUrl, QThread, pyqtSignal, QObject, QPoint, QDir, QTimer, QTime, QStringListModel, QDate

# Importações para o Google Drive
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload

# Mapeamento para exportar tipos de arquivo nativos do Google
EXPORT_MIME_TYPES = {
    'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.google-apps.drawing': 'image/jpeg',
    'application/vnd.google-apps.form': 'application/zip',
}

# Mapeamento de extensões para tipos de arquivo nativos do Google
EXPORT_FILE_EXTENSIONS = {
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
    'image/jpeg': '.jpg',
    'application/zip': '.zip',
}

# Configurações padrão e arquivo de configurações
SETTINGS_FILE = 'settings.json'
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'
THUMBNAIL_CACHE_DIR = 'thumbnails_cache'

def load_settings():
    """Carrega as configurações salvas do arquivo."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    """Salva as configurações no arquivo."""
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
        # Fallback para o desenho antigo se não encontrar o ícone
        # ...existing code for QPainter...
        pixmap = QPixmap(size[0], size[1])
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.drawRect(0, 0, size[0], size[1])
        painter.end()
        return pixmap

def format_size(size_in_bytes):
    """Função auxiliar para formatar o tamanho do arquivo para uma string legível."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024**2:
        return f"{size_in_bytes / 1024:.2f} KB"
    elif size_in_bytes < 1024**3:
        return f"{size_in_bytes / 1024**2:.2f} MB"
    else:
        return f"{size_in_bytes / 1024**3:.2f} GB"

class AuthWorker(QObject):
    authenticated = pyqtSignal(Credentials)
    auth_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        creds = None
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        
        if not os.path.exists(CREDENTIALS_FILE):
            self.auth_failed.emit(f"Erro: Arquivo {CREDENTIALS_FILE} não encontrado. Por favor, adicione-o.")
            return

        try:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

            self.authenticated.emit(creds)
        except Exception as e:
            self.auth_failed.emit(f"Erro de autenticação: {e}. Verifique seu arquivo credentials.json.")

class ThumbnailWorker(QObject):
    finished = pyqtSignal(bytes, str)

    def __init__(self, thumbnail_url, file_id, parent=None):
        super().__init__(parent)
        self.thumbnail_url = thumbnail_url
        self.file_id = file_id
        os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)

    def run(self):
        try:
            response = requests.get(self.thumbnail_url)
            if response.status_code == 200:
                thumbnail_path = os.path.join(THUMBNAIL_CACHE_DIR, f"{self.file_id}.jpg")
                with open(thumbnail_path, 'wb') as f:
                    f.write(response.content)
                self.finished.emit(response.content, thumbnail_path)
            else:
                self.finished.emit(b'', '')
        except Exception as e:
            print(f"Não foi possível baixar a miniatura: {e}")
            self.finished.emit(b'', '')

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
            self.progress_bar.setFormat(f"{percentage}% - {format_size(downloaded_bytes)} de {format_size(total_bytes)}")
            
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
                self.estimated_time_label.setText(f"Tempo estimado: {time_str}")
                self.status_label.setText("Baixando...")
            else:
                self.estimated_time_label.setText("Tempo estimado: Calculando...")

class DownloadWorker(QObject):
    download_started = pyqtSignal(str, int)
    download_progress = pyqtSignal(int, int)
    download_finished = pyqtSignal(str, str)
    download_failed = pyqtSignal(str)

    def __init__(self, service, file_item, parent=None):
        super().__init__(parent)
        self.service = service
        self.file_item = file_item
        self.temp_dir = os.path.join(os.getcwd(), 'Downloads')
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def run(self):
        print("DownloadWorker iniciado para:", self.file_item.get('name'))
        file_id = self.file_item.get('id')
        file_name = self.file_item.get('name')
        mime_type = self.file_item.get('mimeType')
        file_size = self.file_item.get('size', 0)
        web_content_link = self.file_item.get('webContentLink')
        
        self.download_started.emit(file_name, file_size)

        try:
            # Use sempre a API do Google para arquivos do Drive
            if mime_type in EXPORT_MIME_TYPES:
                export_mime = EXPORT_MIME_TYPES[mime_type]
                request = self.service.files().export_media(fileId=file_id, mimeType=export_mime)
                file_extension = EXPORT_FILE_EXTENSIONS.get(export_mime, '.pdf')
                if not file_name.endswith(file_extension):
                    file_name += file_extension
            else:
                request = self.service.files().get_media(fileId=file_id)

            file_path = os.path.join(self.temp_dir, file_name)

            with io.FileIO(file_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        self.download_progress.emit(status.resumable_progress, file_size)

            self.download_finished.emit(file_path, file_name)
        except Exception as e:
            print("Erro no download:", e)
            self.download_failed.emit(f"Não foi possível baixar o arquivo: {e}")

class FileIndexer:
    def __init__(self, db_name='file_index.db'):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                file_id TEXT PRIMARY KEY,
                name TEXT,
                path TEXT,
                mimeType TEXT,
                source TEXT,
                description TEXT,
                thumbnailLink TEXT,
                thumbnailPath TEXT,
                size INTEGER,
                modifiedTime INTEGER,
                createdTime INTEGER,
                parentId TEXT,
                webContentLink TEXT,
                starred INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                name,
                description,
                file_id UNINDEXED,
                source UNINDEXED
            )
        ''')
        self.conn.commit()

    def get_search_suggestions(self, search_term, search_all_sources, limit=10):
        self.cursor.execute("PRAGMA synchronous=OFF")
        
        quoted_term = search_term.strip().replace('"', '""')
        query_term = f'"{quoted_term}*"'
        
        if search_all_sources:
            query = "SELECT name FROM search_index WHERE search_index MATCH ? ORDER BY rank LIMIT ?"
            self.cursor.execute(query, (query_term, limit))
        else:
            query = "SELECT name FROM search_index WHERE search_index MATCH ? AND source = 'local' ORDER BY rank LIMIT ?"
            self.cursor.execute(query, (query_term, limit))
        
        suggestions = [row[0] for row in self.cursor.fetchall()]
        
        self.cursor.execute("PRAGMA synchronous=FULL")
        return list(dict.fromkeys(suggestions))
        
    def save_files_in_batch(self, files_list, source):
        data_files = [
            (
                item.get('id'),
                item.get('name'),
                None,
                item.get('mimeType'),
                item.get('source'),
                item.get('description'),
                item.get('thumbnailLink'),
                item.get('thumbnailPath'),
                item.get('size', 0),
                item.get('modifiedTime'),
                item.get('createdTime'),
                item.get('parentId'),
                item.get('webContentLink'),
                0
            ) for item in files_list
        ]
        self.cursor.executemany("INSERT OR REPLACE INTO files VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data_files)

        data_search_index = [
            (
                item.get('name'),
                item.get('description', ''),
                item.get('id'),
                item.get('source')
            ) for item in files_list
        ]
        self.cursor.executemany("INSERT OR REPLACE INTO search_index VALUES (?, ?, ?, ?)", data_search_index)

        self.conn.commit()

    def clear_cache(self):
        import shutil
        if os.path.exists(THUMBNAIL_CACHE_DIR):
            shutil.rmtree(THUMBNAIL_CACHE_DIR)
        os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)
        self.cursor.execute("UPDATE files SET thumbnailPath = NULL WHERE source = 'drive'")
        self.conn.commit()

    def count_files(self, source, search_term=None, filter_type=None, folder_id=None, advanced_filters=None):
        query_base = "SELECT COUNT(*) FROM files"
        params = []
        where_clauses = []
        
        if source:
            where_clauses.append("source=?")
            params.append(source)
        
        if folder_id:
            where_clauses.append("parentId=?")
            params.append(folder_id)
        elif not search_term:
            where_clauses.append("(parentId IS NULL OR parentId = '')")
        
        if search_term:
            query_base = "SELECT COUNT(*) FROM search_index"
            quoted_search_term = search_term.strip().replace('"', '""')
            query_term = f'"{quoted_search_term}*"'
            query = f"SELECT COUNT(*) FROM search_index WHERE search_index MATCH ?"
            self.cursor.execute(query, (query_term,))
            return self.cursor.fetchone()[0]

        if filter_type == 'image':
            where_clauses.append("mimeType LIKE 'image/%'")
        elif filter_type == 'document':
            where_clauses.append("(mimeType LIKE 'application/vnd.google-apps.document' OR mimeType LIKE 'application/pdf' OR mimeType LIKE '%wordprocessingml.document%')")
        elif filter_type == 'spreadsheet':
            where_clauses.append("(mimeType LIKE 'application/vnd.google-apps.spreadsheet' OR mimeType LIKE '%spreadsheetml.sheet%')")
        elif filter_type == 'presentation':
            where_clauses.append("(mimeType LIKE 'application/vnd.google-apps.presentation' OR mimeType LIKE '%presentationml.presentation%')")
        elif filter_type == 'folder':
            where_clauses.append("mimeType = 'folder' OR mimeType = 'application/vnd.google-apps.folder'")
        
        if advanced_filters:
            if 'size_min' in advanced_filters and advanced_filters['size_min']:
                where_clauses.append("size >= ?")
                params.append(advanced_filters['size_min'] * 1024 * 1024)  # Convertendo MB para bytes
            if 'size_max' in advanced_filters and advanced_filters['size_max']:
                where_clauses.append("size <= ?")
                params.append(advanced_filters['size_max'] * 1024 * 1024)
            if 'modified_after' in advanced_filters and advanced_filters['modified_after']:
                where_clauses.append("modifiedTime >= ?")
                params.append(int(time.mktime(advanced_filters['modified_after'].timetuple())))
            if 'created_after' in advanced_filters and advanced_filters['created_after']:
                where_clauses.append("createdTime >= ?")
                params.append(int(time.mktime(advanced_filters['created_after'].timetuple())))
            if 'created_before' in advanced_filters and advanced_filters['created_before']:
                where_clauses.append("createdTime <= ?")
                params.append(int(time.mktime(advanced_filters['created_before'].timetuple())))
            if 'extension' in advanced_filters and advanced_filters['extension']:
                where_clauses.append("name LIKE ?")
                params.append(f"%{advanced_filters['extension']}")

        query = query_base + " WHERE " + " AND ".join(where_clauses)
        
        self.cursor.execute(query, params)
        return self.cursor.fetchone()[0]

    def load_files_paged(self, source, page, page_size, search_term=None, sort_by='name_asc', filter_type='all', folder_id=None, advanced_filters=None):
        offset = page * page_size
        sort_map = {
            'name_asc': 'name ASC',
            'name_desc': 'name DESC',
            'size_asc': 'size ASC',
            'size_desc': 'size DESC'
        }
        order_by_clause = sort_map.get(sort_by, 'name ASC')

        files_where_clauses = []
        files_params = []

        if not search_term:
            if source:
                files_where_clauses.append("source=?")
                files_params.append(source)
            if folder_id:
                files_where_clauses.append("parentId=?")
                files_params.append(folder_id)
            elif not search_term and not (advanced_filters and advanced_filters.get('extension')):
                files_where_clauses.append("(parentId IS NULL OR parentId = '')")

            if filter_type == 'image':
                files_where_clauses.append("mimeType LIKE 'image/%'")
            elif filter_type == 'document':
                files_where_clauses.append("(mimeType LIKE 'application/vnd.google-apps.document' OR mimeType LIKE 'application/pdf' OR mimeType LIKE '%wordprocessingml.document%')")
            elif filter_type == 'spreadsheet':
                files_where_clauses.append("(mimeType LIKE 'application/vnd.google-apps.spreadsheet' OR mimeType LIKE '%spreadsheetml.sheet%')")
            elif filter_type == 'presentation':
                files_where_clauses.append("(mimeType LIKE 'application/vnd.google-apps.presentation' OR mimeType LIKE '%presentationml.presentation%')")
            elif filter_type == 'folder':
                files_where_clauses.append("mimeType = 'folder' OR mimeType = 'application/vnd.google-apps.folder'")

        if advanced_filters:
            if 'size_min' in advanced_filters and advanced_filters['size_min']:
                files_where_clauses.append("size >= ?")
                files_params.append(advanced_filters['size_min'] * 1024 * 1024)
            if 'size_max' in advanced_filters and advanced_filters['size_max']:
                files_where_clauses.append("size <= ?")
                files_params.append(advanced_filters['size_max'] * 1024 * 1024)
            if 'modified_after' in advanced_filters and advanced_filters['modified_after']:
                files_where_clauses.append("modifiedTime >= ?")
                files_params.append(int(time.mktime(advanced_filters['modified_after'].timetuple())))
            if 'created_after' in advanced_filters and advanced_filters['created_after']:
                files_where_clauses.append("createdTime >= ?")
                files_params.append(int(time.mktime(advanced_filters['created_after'].timetuple())))
            if 'created_before' in advanced_filters and advanced_filters['created_before']:
                files_where_clauses.append("createdTime <= ?")
                files_params.append(int(time.mktime(advanced_filters['created_before'].timetuple())))
            if 'extension' in advanced_filters and advanced_filters['extension']:
                files_where_clauses.append("name LIKE ?")
                files_params.append(f"%{advanced_filters['extension']}")
                files_where_clauses.append("mimeType != 'folder'")
                files_where_clauses.append("mimeType != 'application/vnd.google-apps.folder'")
            if 'is_starred' in advanced_filters and advanced_filters['is_starred']:
                files_where_clauses.append("starred = 1")
                
        if search_term:
            # Extrai frases exatas entre aspas
            quoted_phrases = re.findall(r'"([^"]+)"', search_term)
            # Remove frases das palavras individuais
            search_term_no_quotes = re.sub(r'"[^"]+"', '', search_term)
            # Divide por OR (case insensitive)
            or_groups = [grp.strip() for grp in re.split(r'\s+OR\s+', search_term_no_quotes, flags=re.IGNORECASE) if grp.strip()]
            file_ids_to_fetch = set()
            ranks = []

            # Coleta todos os IDs dos grupos OR
            for group in or_groups:
                terms = [t.strip() for t in re.split(r'\s+', group) if t.strip()]
                positive_terms = [t for t in terms if not t.startswith('-')]
                negative_terms = [t[1:] for t in terms if t.startswith('-') and len(t) > 1]
                quoted_phrases_group = re.findall(r'"([^"]+)"', group)

                fts_clauses = []
                fts_params = []

                # Frases exatas
                for phrase in quoted_phrases_group:
                    fts_clauses.append("search_index MATCH ?")
                    fts_params.append(f'"{phrase}"')

                # Termos positivos
                if positive_terms:
                    pos_terms = [f'"{t.replace("\"", "\"\"")}"*' for t in positive_terms]
                    pos_query = ' '.join(pos_terms)
                    fts_clauses.append("search_index MATCH ?")
                    fts_params.append(pos_query)
                elif not quoted_phrases_group:
                    fts_clauses.append("1=1")

                # Termos negativos (aplicados depois)
                # Não aplique aqui!

                fts_query = "SELECT file_id FROM search_index WHERE " + ' AND '.join(fts_clauses) + " ORDER BY rank LIMIT ? OFFSET ?"
                fts_params.extend([page_size, offset])
                self.cursor.execute(fts_query, fts_params)
                group_ids = [row[0] for row in self.cursor.fetchall()]
                file_ids_to_fetch.update(group_ids)

            file_ids_to_fetch = list(file_ids_to_fetch)
            if not file_ids_to_fetch:
                return []
            
            all_negative_terms = []
            for group in or_groups:
                terms = [t.strip() for t in re.split(r'\s+', group) if t.strip()]
                all_negative_terms.extend([t[1:] for t in terms if t.startswith('-') and len(t) > 1])

            placeholders = ','.join('?' for _ in file_ids_to_fetch)
            details_query = f"SELECT file_id, name, path, mimeType, source, description, thumbnailLink, thumbnailPath, size, modifiedTime, parentId FROM files WHERE file_id IN ({placeholders}) ORDER BY {order_by_clause}"
            self.cursor.execute(details_query, file_ids_to_fetch)
            rows = self.cursor.fetchall()

            # Agora, filtre manualmente os arquivos que contenham o termo negativo
            filtered_rows = []
            for row in rows:
                name = row[1].lower() if row[1] else ""
                description = row[5].lower() if row[5] else ""
                exclude = False
                for neg in all_negative_terms:
                    if neg.lower() in name or neg.lower() in description:
                        exclude = True
                        break
                if not exclude:
                    filtered_rows.append(row)

            self.cursor.execute(f"SELECT rank FROM search_index WHERE file_id IN ({placeholders})", file_ids_to_fetch)
            ranks = [row[0] for row in self.cursor.fetchall()]
            return self._build_file_objects(filtered_rows, ranks)

        else:
            query = f"SELECT file_id, name, path, mimeType, source, description, thumbnailLink, thumbnailPath, size, modifiedTime, parentId FROM files WHERE {' AND '.join(files_where_clauses)} ORDER BY {order_by_clause} LIMIT ? OFFSET ?"
            files_params.extend([page_size, offset])
            self.cursor.execute(query, files_params)

        rows = self.cursor.fetchall()
        files = [
            {
                'id': row[0],
                'name': row[1],
                'path': row[2],
                'mimeType': row[3],
                'source': row[4],
                'description': row[5],
                'thumbnailLink': row[6],
                'thumbnailPath': row[7],
                'size': row[8],
                'modifiedTime': row[9],
                'parentId': row[10]
            } for row in rows
        ]
        return files

    def get_breadcrumb(self, folder_id, source):
        if not folder_id:
            return [{'id': None, 'name': 'Root' if source == 'local' else 'Drive'}]
        
        breadcrumb = []
        current_id = folder_id
        while current_id:
            self.cursor.execute("SELECT file_id, name, path, parentId FROM files WHERE file_id = ?", (current_id,))
            row = self.cursor.fetchone()
            if row:
                breadcrumb.append({'id': row[0], 'name': row[1], 'path': row[2]})
                current_id = row[3]
            else:
                break
        breadcrumb.append({'id': None, 'name': 'Root' if source == 'local' else 'Drive'})
        return list(reversed(breadcrumb))
    
    def _build_file_objects(self, rows, ranks):
        files = []
        for i, row in enumerate(rows):
            file = {
                'id': row[0],
                'name': row[1],
                'path': row[2],
                'mimeType': row[3],
                'source': row[4],
                'description': row[5],
                'thumbnailLink': row[6],
                'thumbnailPath': row[7],
                'size': row[8],
                'modifiedTime': row[9],
                'parentId': row[10],
                'rank': ranks[i] if i < len(ranks) else None
            }
            files.append(file)
        return files
    
    def set_starred(self, file_id, starred=True):
        self.cursor.execute("UPDATE files SET starred = ? WHERE file_id = ?", (1 if starred else 0, file_id))
        self.conn.commit()

    def is_starred(self, file_id):
        self.cursor.execute("SELECT starred FROM files WHERE file_id = ?", (file_id,))
        row = self.cursor.fetchone()
        return bool(row and row[0])

    def close(self):
        self.conn.close()

class LocalScanWorker(QObject):
    finished_signal = pyqtSignal()
    update_status_signal = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    
    def __init__(self, start_paths, db_name='file_index.db', parent=None):
        super().__init__(parent)
        self._is_running = True
        self.start_paths = start_paths
        self.db_name = db_name

    def stop(self):
        self._is_running = False

    def run(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM files WHERE source='local'")
        cursor.execute("DELETE FROM search_index WHERE source='local'")
        conn.commit()
        
        all_found_files = []
        for start_path in self.start_paths:
            self.update_status_signal.emit(f"Escaneando pasta: {start_path}...")
            if not os.path.exists(start_path):
                self.update_status_signal.emit(f"A pasta não existe: {start_path}. Pulando.")
                continue

            try:
                for root, dirs, files in os.walk(start_path):
                    if not self._is_running:
                        break

                    dirs[:] = [d for d in dirs if d not in ['.git', '.cache', 'venv', 'node_modules']]

                    # Adicionar pastas
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        parent_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, root)) if root != start_path else None
                        dir_item = {
                            'id': str(uuid.uuid5(uuid.NAMESPACE_DNS, dir_path)),
                            'name': dir_name,
                            'path': dir_path,
                            'mimeType': 'folder',
                            'description': '',
                            'source': 'local',
                            'thumbnailLink': None,
                            'thumbnailPath': None,
                            'size': 0,
                            'modifiedTime': int(os.path.getmtime(dir_path)),
                            'createdTime': int(os.path.getctime(dir_path)),
                            'parentId': parent_id
                        }
                        all_found_files.append(dir_item)

                    # Adicionar arquivos
                    for file_name in files:
                        if not self._is_running:
                            break
                        file_path = os.path.join(root, file_name)
                        if not os.path.islink(file_path) and os.path.isfile(file_path):
                            mime_type, _ = mimetypes.guess_type(file_path)
                            if mime_type is None:
                                mime_type = 'application/octet-stream'
                            parent_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, root))
                            file_item = {
                                'id': str(uuid.uuid5(uuid.NAMESPACE_DNS, file_path)),
                                'name': file_name,
                                'path': file_path,
                                'mimeType': mime_type,
                                'description': '',
                                'source': 'local',
                                'thumbnailLink': None,
                                'thumbnailPath': None,
                                'size': os.path.getsize(file_path),
                                'modifiedTime': int(os.path.getmtime(file_path)),
                                'createdTime': int(os.path.getctime(file_path)),
                                'parentId': parent_id
                            }
                            all_found_files.append(file_item)

                            if len(all_found_files) % 500 == 0:
                                self.progress_update.emit(len(all_found_files))

            except PermissionError:
                self.update_status_signal.emit(f"Acesso negado para a pasta: {start_path}. Pulando.")
            except Exception as e:
                self.update_status_signal.emit(f"Erro ao escanear a pasta {start_path}: {e}. Pulando.")

            if not self._is_running:
                break

        data_files = [
    (
        item.get('id'),
        item.get('name'),
        item.get('path'),
        item.get('mimeType'),
        item.get('source'),
        item.get('description'),
        item.get('thumbnailLink'),
        item.get('thumbnailPath'),
        item.get('size'),
        item.get('modifiedTime'),
        item.get('createdTime'), 
        item.get('parentId'),
        None,
        0
    ) for item in all_found_files
]
        
        data_search_index = [
            (
                item.get('name'),
                item.get('description', ''),
                item.get('id'),
                item.get('source')
            ) for item in all_found_files
        ]

        cursor.executemany("INSERT OR REPLACE INTO files VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data_files)
        cursor.executemany("INSERT OR REPLACE INTO search_index VALUES (?, ?, ?, ?)", data_search_index)
        conn.commit()
        
        self.update_status_signal.emit("Salvando dados no banco...")
        conn.close()
        
        self.finished_signal.emit()

class DriveSyncWorker(QObject):
    sync_finished = pyqtSignal()
    sync_failed = pyqtSignal(str)
    update_status = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    
    def __init__(self, service, db_name='file_index.db', parent=None):
        super().__init__(parent)
        self.service = service
        self.db_name = db_name

    def run(self):
        self.update_status.emit("Sincronizando arquivos e pastas do Drive...")
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM files WHERE source='drive'")
        cursor.execute("DELETE FROM search_index WHERE source='drive'")
        conn.commit()

        page_token = None
        files_fetched = 0
        fields = "nextPageToken, files(id, name, mimeType, thumbnailLink, webViewLink, webContentLink, description, size, parents, modifiedTime)"
        
        try:
            while True:
                response = self.service.files().list(
                    fields=fields,
                    pageToken=page_token,
                    pageSize=1000
                ).execute()
                
                files = response.get('files', [])
                
                if not files:
                    break
                    
                files_to_save = []
                for f in files:
                    f['source'] = 'drive'
                    f['parentId'] = f.get('parents', [None])[0]
                    f['thumbnailPath'] = None
                    f['webContentLink'] = f.get('webContentLink')
                    f['modifiedTime'] = int(time.mktime(time.strptime(f.get('modifiedTime'), '%Y-%m-%dT%H:%M:%S.%fZ')))
                    created_str = f.get('createdTime')
                    if created_str:
                        try:
                            f['createdTime'] = int(time.mktime(time.strptime(created_str, '%Y-%m-%dT%H:%M:%S.%fZ')))
                        except Exception:
                            try:
                                f['createdTime'] = int(time.mktime(time.strptime(created_str, '%Y-%m-%dT%H:%M:%SZ')))
                            except Exception:
                                f['createdTime'] = f['modifiedTime']
                    else:
                        f['createdTime'] = f['modifiedTime']
                    files_to_save.append(f)
                    files_fetched += 1
                
                data_files = [
                    (
                        item.get('id'),
                        item.get('name'),
                        None,
                        item.get('mimeType'),
                        item.get('source'),
                        item.get('description'),
                        item.get('thumbnailLink'),
                        item.get('thumbnailPath'),
                        item.get('size', 0),
                        item.get('modifiedTime'),
                        item.get('createdTime'),
                        item.get('parentId'),
                        item.get('webContentLink'),
                        0
                    ) for item in files_to_save
                ]
                
                data_search_index = [
                    (
                        item.get('name'),
                        item.get('description', ''),
                        item.get('id'),
                        item.get('source')
                    ) for item in files_to_save
                ]
                
                cursor.executemany("INSERT OR REPLACE INTO files VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data_files)
                cursor.executemany("INSERT OR REPLACE INTO search_index VALUES (?, ?, ?, ?)", data_search_index)
                conn.commit()

                self.progress_update.emit(files_fetched)

                page_token = response.get('nextPageToken', None)
                if not page_token:
                    break

            self.sync_finished.emit()
        except Exception as e:
            self.sync_failed.emit(f"Erro durante a sincronização do Drive: {e}")
            return
        finally:
            conn.close()

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
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(48, 48)
        self.name_label = QLabel(self.file_item.get('name', 'Nome Desconhecido'))
        self.name_label.setFont(QFont("Arial", 10))
        self.name_label.setWordWrap(False)
        
        source_name = "Local" if self.file_item.get('source') == 'local' else "Drive"
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

        self.star_button = QPushButton("★" if parent_app.indexer.is_starred(file_item.get('id')) else "☆")
        self.star_button.setFixedWidth(30)
        self.star_button.setStyleSheet("font-size: 18px; border: none; background: transparent;")
        self.star_button.clicked.connect(self.toggle_starred)
        self.main_layout.addWidget(self.star_button)
        
        self.load_thumbnail()

    def toggle_starred(self):
        is_now_starred = not self.parent_app.indexer.is_starred(self.file_item.get('id'))
        self.parent_app.indexer.set_starred(self.file_item.get('id'), is_now_starred)
        self.star_button.setText("★" if is_now_starred else "☆")
        self.status_bar_callback("Marcado como favorito." if is_now_starred else "Desmarcado como favorito.")

    def apply_theme_style(self):
        bg_color = QApplication.palette().color(QPalette.ColorRole.Window)
        luminosity = 0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()
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
        mime_type = self.file_item.get('mimeType')
        is_image = mime_type.startswith('image/')
        is_video = mime_type.startswith('video/')
        thumbnail_url = self.file_item.get('thumbnailLink')
        thumbnail_path = self.file_item.get('thumbnailPath')

        if self.file_item.get('source') == 'local':
            if is_image:
                pixmap = QPixmap(self.file_item.get('path'))
                if pixmap.isNull():
                    pixmap = get_generic_thumbnail(mime_type)
            elif is_video:
                pixmap = self.get_video_thumbnail(self.file_item.get('path'))
                if pixmap.isNull():
                    pixmap = get_generic_thumbnail(mime_type)
            else:
                pixmap = get_generic_thumbnail(mime_type)
            self.set_thumbnail(pixmap)
        elif thumbnail_path and os.path.exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            if not pixmap.isNull():
                self.set_thumbnail(pixmap)
            else:
                self.set_thumbnail(get_generic_thumbnail(mime_type))
        elif thumbnail_url:
            # Tenta baixar thumbnail do Drive para qualquer tipo de arquivo
            self.set_thumbnail(get_generic_thumbnail(mime_type))
            self.thumbnail_thread = QThread()
            self.thumbnail_worker = ThumbnailWorker(thumbnail_url, self.file_item.get('id'))
            self.thumbnail_worker.moveToThread(self.thumbnail_thread)
            self.thumbnail_thread.started.connect(self.thumbnail_worker.run)
            self.thumbnail_worker.finished.connect(self.on_thumbnail_loaded)
            self.thumbnail_thread.start()
        else:
            self.set_thumbnail(get_generic_thumbnail(mime_type))

    def get_video_thumbnail(self, video_path):
        try:
            cap = cv2.VideoCapture(video_path)
            success, frame = cap.read()
            cap.release()
            if success and frame is not None:
                # Converte o frame para QImage
                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
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

        if image_data and thumbnail_path:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                self.set_thumbnail(pixmap)
                conn = sqlite3.connect('file_index.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE files SET thumbnailPath = ? WHERE file_id = ?", (thumbnail_path, self.file_item.get('id')))
                conn.commit()
                conn.close()
            else:
                self.set_thumbnail(get_generic_thumbnail(self.file_item.get('mimeType')))
        else:
            self.set_thumbnail(get_generic_thumbnail(self.file_item.get('mimeType')))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.file_item.get('mimeType') == 'application/vnd.google-apps.folder' or self.file_item.get('mimeType') == 'folder':
                self.folder_clicked.emit(self.file_item.get('id'))
            else:
                self.selected.emit(self.file_item)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Só faz drag se não for pasta
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
                QMessageBox.critical(self, "Erro ao Abrir Arquivo", f"Não foi possível abrir o arquivo: {e}")
        else:
            self.download_thread = QThread()
            self.download_worker = DownloadWorker(self.service, self.file_item)
            self.download_worker.moveToThread(self.download_thread)
        
            self.download_worker.download_started.connect(lambda name, size: self.status_bar_callback(f"Baixando {name}..."))
            self.download_worker.download_finished.connect(self.on_download_finished_and_open)
            self.download_worker.download_failed.connect(lambda error: QMessageBox.critical(self, "Erro de Download", error))
        
            self.download_thread.started.connect(self.download_worker.run)
            self.download_thread.start()
    
    def on_download_finished_and_open(self, file_path, file_name):
        QMessageBox.information(self, "Download Concluído", f"O arquivo '{file_name}' foi baixado com sucesso.")
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            else:
                webbrowser.open_new_tab(f'file:///{file_path}')
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Abrir Arquivo", f"Não foi possível abrir o arquivo: {e}")
        
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
        self.download_worker.download_progress.connect(self.on_download_progress)
        self.download_worker.download_finished.connect(self.on_download_finished)
        self.download_worker.download_failed.connect(self.on_download_failed)
        
        self.download_thread.started.connect(self.download_worker.run)
        self.download_thread.start()
        
    def on_download_started(self, file_name, file_size):
        if file_size > 5 * 1024 * 1024:
            self.download_dialog = DownloadProgressDialog(file_name, self.parent_app)
            self.download_dialog.show()
        else:
            self.status_bar_callback(f"Baixando {file_name}...")
        
    def on_download_progress(self, downloaded_bytes, total_bytes):
        if self.download_dialog:
            self.download_dialog.update_progress(downloaded_bytes, total_bytes)

    def do_drag(self):
        # Se o arquivo é local ou já baixado, faz o drag normalmente
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

        # Para arquivos do Drive, só baixa automaticamente se for pequeno
        mime_type = self.file_item.get('mimeType')
        file_size = self.file_item.get('size', 0)
        is_small_file = file_size < 5 * 1024 * 1024  # 5 MB

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
            # Para arquivos grandes, apenas mostra mensagem
            self.status_bar_callback("Arraste arquivos grandes apenas após baixá-los pelo botão de download.")

    def on_download_finished(self, file_path, file_name):
        self.download_in_progress = False
        self.local_file_path = file_path
        self.status_bar_callback(f"Download de {file_name} concluído.")

        conn = sqlite3.connect('file_index.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE files SET path = ? WHERE file_id = ?", (file_path, self.file_item.get('id')))
        conn.commit()
        conn.close()
        
        if self.download_dialog:
            self.download_dialog.accept()
            self.download_dialog = None

        self.status_bar_callback(f"Download de {file_name} concluído. Agora você pode arrastá-lo para qualquer lugar.")

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
                self.main_layout.insertWidget(self.main_layout.count() - 2, checkbox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
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
        folder_path = QFileDialog.getExistingDirectory(self, "Selecione a Pasta para Adicionar")
        if folder_path and folder_path not in self.custom_paths:
            self.custom_paths.append(folder_path)
            checkbox = QCheckBox(f"Customizada: {folder_path}")
            checkbox.setChecked(True)
            self.checkboxes[folder_path] = checkbox
            self.main_layout.insertWidget(self.main_layout.count() - 2, checkbox)

    def get_selected_paths(self):
        selected_paths = []
        for name, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                path = self.default_paths.get(name) or name
                selected_paths.append(path)

        return selected_paths

class DriveFileGalleryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoxImago - Galeria de Arquivos")
        self.setMinimumSize(600, 400)

        self.service = None
        self.indexer = FileIndexer()
        self.current_view = 'local'
        self.current_page = 0
        self.page_size = 50
        self.search_term = ""
        self.current_filter = "all"
        self.current_sort = "name_asc"
        self.current_folder_id = None
        self.advanced_filters = {}
        self.is_loading = False
        self.all_files_loaded = False
        self.is_authenticated = False

        self.auth_thread = None
        self.auth_worker = None
        self.local_scan_thread = None
        self.local_scan_worker = None
        self.drive_sync_thread = None
        self.drive_sync_worker = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.handle_search_request)

        self.suggestion_timer = QTimer()
        self.suggestion_timer.setSingleShot(True)
        self.suggestion_timer.timeout.connect(self.update_search_suggestions)
        
        self.completer_model = QStringListModel()

        self._setup_ui()
        self.show()
        self._check_initial_auth()

        settings = load_settings()
        scan_paths = settings.get('scan_paths')
        if scan_paths:
            self._start_local_scan(scan_paths)
        else:
            # Se não houver configuração, use as pastas padrão do OptionsDialog
            default_paths = OptionsDialog()._get_default_folders().values()
            self._start_local_scan(list(default_paths))

    def closeEvent(self, event):
        for i in range(self.files_layout.count()):
            item = self.files_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, FileItemWidget):
                widget.cleanup()

        if self.local_scan_thread and self.local_scan_thread.isRunning():
            self.local_scan_worker.stop()
            self.local_scan_thread.quit()
            self.local_scan_thread.wait()
        
        if self.drive_sync_thread and self.drive_sync_thread.isRunning():
            self.drive_sync_thread.quit()
            self.drive_sync_thread.wait()

        self.indexer.close()
        event.accept()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        unified_bar = QFrame()
        unified_bar.setFrameShape(QFrame.Shape.StyledPanel)
        unified_bar.setFrameShadow(QFrame.Shadow.Raised)
        unified_bar.setFixedHeight(50)

        unified_layout = QHBoxLayout(unified_bar)
        unified_layout.setContentsMargins(10, 5, 10, 5)

        self.app_title_label = QLabel("VI-MB")
        self.app_title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        unified_layout.addWidget(self.app_title_label)
        unified_layout.addSpacing(15)
        
        self.view_label = QLabel("Visualizando: Local")
        self.view_label.setFixedWidth(150)
        unified_layout.addWidget(self.view_label)

        unified_layout.addStretch()

        self.breadcrumb_layout = QHBoxLayout()
        self.breadcrumb_widget = QWidget()
        self.breadcrumb_widget.setLayout(self.breadcrumb_layout)
        unified_layout.addWidget(self.breadcrumb_widget)

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Pesquisar...")
        self.search_entry.setFixedWidth(250)
        self.search_entry.textChanged.connect(self.handle_search_input)
        unified_layout.addWidget(self.search_entry)
        unified_layout.addStretch()
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Todos os Tipos", "all")
        self.filter_combo.addItem("Imagens", "image")
        self.filter_combo.addItem("Documentos", "document")
        self.filter_combo.addItem("Planilhas", "spreadsheet")
        self.filter_combo.addItem("Apresentações", "presentation")
        self.filter_combo.addItem("Pastas", "folder")
        self.filter_combo.activated.connect(self.change_filter_type_combo)
        self.filter_combo.setEnabled(False)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Nome (A-Z)", "name_asc")
        self.sort_combo.addItem("Nome (Z-A)", "name_desc")
        self.sort_combo.addItem("Tamanho (Menor)", "size_asc")
        self.sort_combo.addItem("Tamanho (Maior)", "size_desc")
        self.sort_combo.activated.connect(self.change_sort_order)
        self.sort_combo.setEnabled(False)
        
        unified_layout.addWidget(QLabel("Filtrar:"))
        unified_layout.addWidget(self.filter_combo)
        unified_layout.addSpacing(10)
        unified_layout.addWidget(QLabel("Ordenar por:"))
        unified_layout.addWidget(self.sort_combo)

        # Filtros Avançados
        self.advanced_filter_layout = QHBoxLayout()
        self.extension_combo = QComboBox()
        self.extension_combo.setEditable(False)
        self.extension_combo.setPlaceholderText("Selecione a extensão")
        self._populate_extension_combo()
        self.modified_after_date = QDateEdit()
        self.modified_after_date.setDate(QDate.currentDate().addDays(-7))
        self.modified_after_date.setCalendarPopup(True)
        self.apply_advanced_filter_button = QPushButton("Aplicar Filtros")
        self.apply_advanced_filter_button.clicked.connect(self.apply_advanced_filters)
        self.created_after_date = QDateEdit()
        self.created_after_date.setDate(QDate.currentDate().addDays(-7))
        self.created_after_date.setCalendarPopup(True)
        self.created_before_date = QDateEdit()
        self.created_before_date.setDate(QDate.currentDate())
        self.created_before_date.setCalendarPopup(True)

        self.clear_advanced_filter_button = QPushButton("Limpar Filtros")
        self.clear_advanced_filter_button.clicked.connect(self.clear_advanced_filters)

        self.advanced_filter_layout.addWidget(QLabel("Extensão:"))
        self.advanced_filter_layout.addWidget(self.extension_combo)
        self.advanced_filter_layout.addWidget(QLabel("Criado antes:"))
        self.advanced_filter_layout.addWidget(self.created_before_date)
        self.advanced_filter_layout.addWidget(QLabel("Criado após:"))
        self.advanced_filter_layout.addWidget(self.created_after_date)
        self.advanced_filter_layout.addWidget(QLabel("Modificado após:"))
        self.advanced_filter_layout.addWidget(self.modified_after_date)
        self.starred_checkbox = QCheckBox("Favoritos")
        self.advanced_filter_layout.addWidget(self.starred_checkbox)
        self.advanced_filter_layout.addWidget(self.apply_advanced_filter_button)
        self.advanced_filter_layout.addWidget(self.clear_advanced_filter_button)


        main_layout.addLayout(self.advanced_filter_layout)

        unified_layout.addStretch()
        
        self.scan_options_button = QPushButton("Pastas Locais")
        self.scan_options_button.clicked.connect(self._show_scan_options)

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self._start_auth)

        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.handle_logout)
        
        self.auth_status_label = QLabel("Verificando...")
        self.auth_status_label.setFixedWidth(150)

        self.clear_cache_button = QPushButton("Limpar Cache")
        self.clear_cache_button.clicked.connect(self.clear_thumbnail_cache)

        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.search_entry.setCompleter(self.completer)
        
        unified_layout.addWidget(self.scan_options_button)
        unified_layout.addWidget(self.auth_status_label)
        unified_layout.addWidget(self.login_button)
        unified_layout.addWidget(self.logout_button)
        unified_layout.addWidget(self.clear_cache_button)
        
        main_layout.addWidget(unified_bar)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        
        self.files_layout = QVBoxLayout(self.scroll_content)
        self.files_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_content.setLayout(self.files_layout)
        self.scroll_area.setWidget(self.scroll_content)
        
        self.details_panel = FileDetailsPanel(self)
        
        self.splitter.addWidget(self.scroll_area)
        self.splitter.addWidget(self.details_panel)
        self.details_panel.setMinimumWidth(320)
        self.details_panel.setMaximumWidth(340)
        self.splitter.setSizes([900, 340])
        
        main_layout.addWidget(self.splitter)

        self.loading_label = QLabel("Carregando...")
        self.loading_label.setFixedHeight(30)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.hide()
        main_layout.addWidget(self.loading_label)

        self.status_bar = self.statusBar()
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.progress_bar, 1)

        self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll)

        self.all_loaded_label = QLabel("Todos os arquivos foram carregados.")
        self.all_loaded_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.all_loaded_label.setFixedHeight(30)  # Limita a altura do label
        self.all_loaded_label.hide()
        main_layout.addWidget(self.all_loaded_label)
        
        self.update_ui_for_auth_state(False)
        self.update_ui_for_view()
        self.update_filter_buttons()
        self.update_breadcrumb()

        self.extension_combo.currentIndexChanged.connect(self.apply_advanced_filters)
        self.modified_after_date.dateChanged.connect(self.apply_advanced_filters)
        self.created_after_date.dateChanged.connect(self.apply_advanced_filters)
        self.created_before_date.dateChanged.connect(self.apply_advanced_filters)
        self.starred_checkbox.stateChanged.connect(self.apply_advanced_filters)

    def _populate_extension_combo(self):
        self.extension_combo.clear()
        self.extension_combo.addItem("Todas", "")  # opção para não filtrar
        # Busca extensões únicas no banco
        self.indexer.cursor.execute("SELECT DISTINCT name FROM files")
        extensions = set()
        for row in self.indexer.cursor.fetchall():
            name = row[0]
            ext = os.path.splitext(name)[1].lower()
            if ext:
                extensions.add(ext)
        for ext in sorted(extensions):
            self.extension_combo.addItem(ext, ext)

    def apply_advanced_filters(self):
        filters = {}

        # Extensão
        if self.extension_combo.currentData():
            filters['extension'] = self.extension_combo.currentData()

        # Modificado após
        default_modified = QDate.currentDate().addDays(-7)
        if self.modified_after_date.date() != default_modified:
            filters['modified_after'] = self.modified_after_date.date().toPyDate()

        # Criado após
        default_created_after = QDate.currentDate().addDays(-7)
        if self.created_after_date.date() != default_created_after:
            filters['created_after'] = self.created_after_date.date().toPyDate()

        # Criado antes
        default_created_before = QDate.currentDate()
        if self.created_before_date.date() != default_created_before:
            filters['created_before'] = self.created_before_date.date().toPyDate()

        if self.starred_checkbox.isChecked():
            filters['is_starred'] = True

        self.advanced_filters = filters
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def clear_advanced_filters(self):
        self.extension_combo.setCurrentIndex(0)
        self.modified_after_date.setDate(QDate.currentDate().addDays(-7))
        self.created_after_date.setDate(QDate.currentDate().addDays(-7))
        self.created_before_date.setDate(QDate.currentDate())
        self.advanced_filters = {}
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()
        self.starred_checkbox.setChecked(False)

    def clear_thumbnail_cache(self):
        self.indexer.clear_cache()
        self.status_bar.showMessage("Cache de miniaturas limpo.", 5000)
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def update_breadcrumb(self):
        # Limpa o layout
        for i in reversed(range(self.breadcrumb_layout.count())):
            item = self.breadcrumb_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        breadcrumb = self.indexer.get_breadcrumb(self.current_folder_id, self.current_view)
        for i, crumb in enumerate(breadcrumb):
            label = ClickableLabel(crumb['name'])
            label.setStyleSheet("font-weight: bold; text-decoration: underline;")
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            # Navega para o id correspondente (None para raiz)
            label.clicked.connect(lambda checked=False, fid=crumb['id']: self.navigate_to_folder(fid))
            self.breadcrumb_layout.addWidget(label)
            if i < len(breadcrumb) - 1:
                self.breadcrumb_layout.addWidget(QLabel(" > "))
        self.breadcrumb_layout.addStretch()

    def navigate_to_root(self, source):
        self.current_view = None
        self.current_folder_id = None
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()
        self.update_breadcrumb()

    def navigate_to_folder(self, folder_id):
        self.search_term = ""  # Limpa a busca ao navegar para uma pasta
        self.search_entry.clear()
        self.current_folder_id = folder_id
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()
        self.update_breadcrumb()

    def update_filter_buttons(self):
        is_searching = bool(self.search_term)
        self.filter_combo.setEnabled(not is_searching)
        self.sort_combo.setEnabled(not is_searching)
        
    def update_ui_for_view(self):
        view_name = "Local" if self.current_view == 'local' else "Google Drive"
        if self.search_term:
            view_name = "Pesquisa Unificada"
        self.view_label.setText(f"Visualizando: {view_name}")
        self.update_breadcrumb()

    def change_filter_type_combo(self, index):
        self.current_filter = self.filter_combo.itemData(index)
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def change_sort_order(self, index):
        self.current_sort = self.sort_combo.itemData(index)
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def handle_search_input(self, text):
        if text:
            self.search_timer.stop()
            self.search_timer.start(500)
            self.update_search_suggestions()
        else:
            self.search_timer.stop()
            self.search_term = ""
            self.completer_model.setStringList([])
            self.current_page = 0
            self.all_files_loaded = False
            self.current_folder_id = None
            self.clear_display()
            self.load_next_batch()
            
        self.update_filter_buttons()
        self.update_ui_for_view()

    def update_search_suggestions(self):
        text = self.search_entry.text().strip()
        if not text:
            self.completer_model.setStringList([])
            return

        suggestions = self.indexer.get_search_suggestions(text, self.is_authenticated)
        self.completer_model.setStringList(suggestions)

    def handle_search_request(self):
        self.search_term = self.search_entry.text().strip().lower()
        self.current_page = 0
        self.all_files_loaded = False
        self.current_folder_id = None
        self.clear_display()
        self.load_next_batch()

    def update_ui_for_auth_state(self, is_authenticated):
        self.is_authenticated = is_authenticated
        self.login_button.setVisible(not is_authenticated)
        self.logout_button.setVisible(is_authenticated)

    def on_scroll(self, value):
        scroll_bar = self.scroll_area.verticalScrollBar()
        if value > 0 and value == scroll_bar.maximum() and not self.is_loading and not self.all_files_loaded:
            self.load_next_batch()

    def _show_scan_options(self):
        if self.local_scan_thread and self.local_scan_thread.isRunning():
            QMessageBox.warning(self, "Aviso", "Aguarde a conclusão do escaneamento local.")
            return

        dialog = OptionsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_paths = dialog.get_selected_paths()
            settings = load_settings()
            settings['scan_paths'] = selected_paths
            save_settings(settings)

            if selected_paths:
                self._start_local_scan(selected_paths)
            else:
                QMessageBox.information(self, "Aviso", "Nenhuma pasta selecionada. O escaneamento local não foi iniciado.")
                self.current_view = 'local'
                self.load_next_batch()

    def _start_local_scan(self, paths_to_scan):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.all_loaded_label.hide()

        self.local_scan_thread = QThread()
        self.local_scan_worker = LocalScanWorker(start_paths=paths_to_scan, db_name=self.indexer.db_name)
        self.local_scan_worker.moveToThread(self.local_scan_thread)

        self.local_scan_worker.finished_signal.connect(self.on_local_scan_finished)
        self.local_scan_worker.update_status_signal.connect(self.status_bar.showMessage)
        self.local_scan_worker.progress_update.connect(self.update_local_scan_progress)

        self.local_scan_thread.started.connect(self.local_scan_worker.run)
        self.local_scan_thread.start()

    def on_local_scan_finished(self):
        self.status_bar.showMessage("Escaneamento local concluído.", 5000)
        self.progress_bar.setVisible(False)
        self.local_scan_thread.quit()
        self.local_scan_thread.wait()
        self.local_scan_worker.deleteLater()
        self.local_scan_thread.deleteLater()
        self.local_scan_worker = None
        self.local_scan_thread = None
        
        self.current_view = 'local'
        self.clear_display()
        self.load_next_batch()

    def update_local_scan_progress(self, files_found):
        self.status_bar.showMessage(f"Escaneando... {files_found} arquivos encontrados.")

    def _check_initial_auth(self):
        self.update_ui_for_auth_state(False)
        self.auth_status_label.setText("Verificando credenciais...")
        
        creds = None
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if creds and creds.valid:
                self.service = build('drive', 'v3', credentials=creds)
                self.update_ui_for_auth_state(True)
                self.auth_status_label.setText("Logado com Google")
                self._start_drive_sync()
            elif creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.service = build('drive', 'v3', credentials=creds)
                    self.update_ui_for_auth_state(True)
                    self.auth_status_label.setText("Logado com Google")
                    with open(TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
                    self._start_drive_sync()
                except Exception as e:
                    self.status_bar.showMessage(f"Sessão expirada. Faça login novamente.", 5000)
                    self.handle_logout()
        else:
            self.auth_status_label.setText("Não Autenticado")
            self.load_next_batch()

    def _start_auth(self):
        if self.auth_thread and self.auth_thread.isRunning():
            self.status_bar.showMessage("Processo de login já em andamento...", 5000)
            return

        self.status_bar.showMessage("Abrindo navegador para autenticação...", 5000)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.login_button.setEnabled(False)

        self.auth_thread = QThread()
        self.auth_worker = AuthWorker()
        self.auth_worker.moveToThread(self.auth_thread)

        self.auth_worker.authenticated.connect(self.on_auth_success)
        self.auth_worker.auth_failed.connect(self.on_auth_fail)

        self.auth_thread.started.connect(self.auth_worker.run)
        self.auth_thread.start()

    def on_auth_success(self, creds):
        self.progress_bar.setVisible(False)
        self.login_button.setEnabled(True)
        self.status_bar.showMessage("Login bem-sucedido. Sincronizando arquivos...", 5000)
        self.auth_status_label.setText("Logado com Google")
        self.service = build('drive', 'v3', credentials=creds)
        self.update_ui_for_auth_state(True)
        self._start_drive_sync()

        self.auth_thread.quit()
        self.auth_thread.wait()
        self.auth_worker.deleteLater()
        self.auth_thread.deleteLater()
        self.auth_worker = None
        self.auth_thread = None

    def on_auth_fail(self, error_message):
        self.progress_bar.setVisible(False)
        self.login_button.setEnabled(True)
        QMessageBox.critical(self, "Erro de Autenticação", error_message)
        self.status_bar.showMessage("Login falhou.", 5000)
        self.auth_status_label.setText("Não Autenticado")

        self.auth_thread.quit()
        self.auth_thread.wait()
        self.auth_worker.deleteLater()
        self.auth_thread.deleteLater()
        self.auth_worker = None
        self.auth_thread = None
        
    def handle_logout(self):
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            self.status_bar.showMessage("Logout bem-sucedido.", 5000)
            self.service = None
            self.indexer.cursor.execute("DELETE FROM files WHERE source='drive'")
            self.indexer.cursor.execute("DELETE FROM search_index WHERE source='drive'")
            self.indexer.conn.commit()
            self.clear_display()
            self.update_ui_for_auth_state(False)
            self.auth_status_label.setText("Não Autenticado")
            
            self.current_view = 'local'
            self.current_folder_id = None
            self.load_next_batch()

    def _start_drive_sync(self):
        if self.drive_sync_thread and self.drive_sync_thread.isRunning():
            self.status_bar.showMessage("Sincronização do Drive já em andamento...", 5000)
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.drive_sync_thread = QThread()
        self.drive_sync_worker = DriveSyncWorker(self.service, db_name=self.indexer.db_name)
        self.drive_sync_worker.moveToThread(self.drive_sync_thread)

        self.drive_sync_worker.sync_finished.connect(self.on_drive_sync_finished)
        self.drive_sync_worker.sync_failed.connect(self.on_drive_sync_failed)
        self.drive_sync_worker.update_status.connect(self.status_bar.showMessage)
        self.drive_sync_worker.progress_update.connect(self.update_drive_sync_progress)

        self.drive_sync_thread.started.connect(self.drive_sync_worker.run)
        self.drive_sync_thread.start()

    def on_drive_sync_finished(self):
        self.status_bar.showMessage("Sincronização do Drive concluída.", 5000)
        self.progress_bar.setVisible(False)
        self.drive_sync_thread.quit()
        self.drive_sync_thread.wait()
        self.drive_sync_worker.deleteLater()
        self.drive_sync_thread.deleteLater()
        self.drive_sync_worker = None
        self.drive_sync_thread = None

        self.current_view = 'drive'
        self.current_folder_id = None
        self.clear_display()
        self.load_next_batch()

    def on_drive_sync_failed(self, error_message):
        self.status_bar.showMessage(error_message, 5000)
        self.progress_bar.setVisible(False)
        self.drive_sync_thread.quit()
        self.drive_sync_thread.wait()
        self.drive_sync_worker.deleteLater()
        self.drive_sync_thread.deleteLater()
        self.drive_sync_worker = None
        self.drive_sync_thread = None
        self.update_ui_for_auth_state(False)

    def update_drive_sync_progress(self, current_value):
        self.status_bar.showMessage(f"Sincronizando... {current_value} arquivos encontrados.")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(current_value)

    def clear_display(self):
        self.all_loaded_label.hide()
        for i in reversed(range(self.files_layout.count())):
            item = self.files_layout.itemAt(i)
            widget = item.widget()
            if widget:
                if hasattr(widget, 'cleanup'):
                    widget.cleanup()
                widget.deleteLater()
        
        self.details_panel.hide()

    def load_next_batch(self):
        if self.is_loading or self.all_files_loaded:
            return

        self.is_loading = True
        self.loading_label.show()
        QApplication.processEvents()
        
        search_all_sources = bool(self.search_term and self.is_authenticated)
        source = self.current_view if not search_all_sources else None

        start_time = time.time()

        folder_id = self.current_folder_id 
        filter_type = self.current_filter

        if not self.search_term and folder_id is None:
            # Se filtro de favoritos está ativo, não force 'folder'
            if self.advanced_filters.get('is_starred'):
                filter_type = 'all'
            elif self.advanced_filters.get('extension'):
                filter_type = 'all'
            else:
                filter_type = 'folder'
            local_folders = self.indexer.load_files_paged(
                'local', 0, 100, None, self.current_sort, filter_type, None, self.advanced_filters
            )
            drive_folders = []
            if self.is_authenticated:
                drive_folders = self.indexer.load_files_paged(
                    'drive', 0, 100, None, self.current_sort, filter_type, None, self.advanced_filters
                )
            files_to_add = local_folders + drive_folders
        else:
            # Se filtro de extensão está ativo, não force 'folder'
            if self.advanced_filters.get('extension'):
                filter_type = 'all'
            files_to_add = self.indexer.load_files_paged(
                source, self.current_page, self.page_size, self.search_term,
                self.current_sort, filter_type, folder_id, self.advanced_filters
            )
        

        elapsed_time = time.time() - start_time
        print(f"Tempo para carregar {len(files_to_add)} arquivos do banco de dados: {elapsed_time:.4f}s")

        if not files_to_add:
            self.all_files_loaded = True
            if self.files_layout.count() == 0:
                self.loading_label.setText("Nenhum arquivo encontrado.")
                self.loading_label.show()
            else:
                self.loading_label.hide()
                self.all_loaded_label.show()
        else:
            self._add_thumbnail_widgets(files_to_add)
            self.current_page += 1
            self.loading_label.hide()

        self.is_loading = False

    def _add_thumbnail_widgets(self, files_to_add):
        for item in files_to_add:
            item_widget = FileItemWidget(self, item, self.service, self.status_bar.showMessage)
            item_widget.selected.connect(self.details_panel.update_details)
            item_widget.folder_clicked.connect(self.navigate_to_folder)
            self.files_layout.addWidget(item_widget)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace:
            # Se não estiver na raiz, volta para a pasta pai
            if self.current_folder_id:
                self.go_to_parent_folder()
            else:
                # Se já está na raiz, não faz nada ou pode dar um feedback
                pass
        else:
            super().keyPressEvent(event)

    def go_to_parent_folder(self):
        # Busca o parentId da pasta atual
        self.indexer.cursor.execute("SELECT parentId FROM files WHERE file_id = ?", (self.current_folder_id,))
        row = self.indexer.cursor.fetchone()
        parent_id = row[0] if row else None
        self.navigate_to_folder(parent_id)

class FileDetailsPanel(QFrame):
    # ...classe FileDetailsPanel...

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        # Área de rolagem
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Widget de conteúdo
        self.content_widget = QWidget()
        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.title_label = QLabel("Detalhes do Arquivo")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(192, 192)
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

        self.form_layout.addRow(QLabel("<b>Nome:</b>"), self.name_label)
        self.form_layout.addRow(QLabel("<b>Fonte:</b>"), self.source_label)
        self.form_layout.addRow(QLabel("<b>Tamanho:</b>"), self.size_label)
        self.form_layout.addRow(QLabel("<b>Caminho/Link:</b>"), self.path_label)
        self.form_layout.addRow(QLabel("<b>Descrição:</b>"), self.description_label)

        self.download_button = QPushButton("Baixar Arquivo")
        self.download_button.setVisible(False)
        self.download_button.clicked.connect(self.download_file)
        self.form_layout.addRow(QLabel(""), self.download_button)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)

        # Layout principal do painel
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll_area)

        self.current_file_item = None
        self.parent_app = parent
        self.temp_download_widget = None

        self.hide()

    def update_details(self, file_item):
        self.title_label.setText("Detalhes do Arquivo")
        self.name_label.setText(file_item.get('name', 'N/A'))
        self.source_label.setText("Google Drive" if file_item.get('source') == 'drive' else "Local")
        self.size_label.setText(format_size(file_item.get('size', 0)) if file_item.get('mimeType') not in ['application/vnd.google-apps.folder', 'folder'] else "N/A")
        self.path_label.setText(file_item.get('path', file_item.get('webViewLink', 'N/A')))
        self.description_label.setText(file_item.get('description', 'N/A'))
        self.current_file_item = file_item

        # Limpa a thumbnail para evitar mostrar a anterior
        self.thumbnail_label.setPixmap(get_generic_thumbnail(file_item.get('mimeType'), size=(96, 96)))

        # Mostra o botão apenas para arquivos que podem ser baixados
        if file_item.get('source') == 'drive' and file_item.get('mimeType') not in ['application/vnd.google-apps.folder', 'folder']:
            self.download_button.setVisible(True)
        else:
            self.download_button.setVisible(False)
        self.show()

        thumbnail_path = file_item.get('thumbnailPath')
        thumbnail_link = file_item.get('thumbnailLink')

        # 1. Tenta usar thumbnail do cache
        if thumbnail_path and os.path.exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            if not pixmap.isNull():
                self.thumbnail_label.setPixmap(pixmap.scaled(
                    self.thumbnail_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                return  # Já exibiu a thumbnail, não precisa baixar

        # 2. Se for arquivo do Drive e tiver thumbnailLink, tenta baixar a thumbnail
        if file_item.get('source') == 'drive' and thumbnail_link:
            self.thumbnail_thread = QThread()
            self.thumbnail_worker = ThumbnailWorker(thumbnail_link, file_item.get('id'))
            self.thumbnail_worker.moveToThread(self.thumbnail_thread)
            self.thumbnail_thread.started.connect(self.thumbnail_worker.run)
            self.thumbnail_worker.finished.connect(self.on_thumbnail_loaded)
            self.thumbnail_thread.start()

    def on_thumbnail_loaded(self, image_data, thumbnail_path):
        if self.thumbnail_worker and self.thumbnail_thread:
            self.thumbnail_thread.quit()
            self.thumbnail_thread.wait()
            self.thumbnail_worker.deleteLater()
            self.thumbnail_thread.deleteLater()
            self.thumbnail_worker = None
            self.thumbnail_thread = None

        if image_data and thumbnail_path:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                self.thumbnail_label.setPixmap(pixmap.scaled(
                    self.thumbnail_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                # Atualiza o banco para futuras consultas
                conn = sqlite3.connect('file_index.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE files SET thumbnailPath = ? WHERE file_id = ?", (thumbnail_path, self.current_file_item.get('id')))
                conn.commit()
                conn.close()
            else:
                self.thumbnail_label.setPixmap(get_generic_thumbnail(self.current_file_item.get('mimeType'), size=(96, 96)))
        else:
            self.thumbnail_label.setPixmap(get_generic_thumbnail(self.current_file_item.get('mimeType'), size=(96, 96)))

    def download_file(self):
        if self.current_file_item and self.parent_app and hasattr(self.parent_app, 'service'):
            from PyQt6.QtWidgets import QMessageBox
            if self.parent_app.service is None:
                QMessageBox.warning(self, "Aviso", "Você precisa estar autenticado no Google Drive para baixar arquivos.")
                return

            self.download_dialog = DownloadProgressDialog(self.current_file_item.get('name'), self)
            self.download_dialog.show()

            self.download_thread = QThread(self)
            self.download_worker = DownloadWorker(self.parent_app.service, self.current_file_item)
            self.download_worker.moveToThread(self.download_thread)

            self.download_worker.download_progress.connect(self.download_dialog.update_progress)
            self.download_worker.download_finished.connect(lambda path, name: self.download_dialog.accept())
            self.download_worker.download_finished.connect(lambda path, name: QMessageBox.information(self, "Download concluído", f"O arquivo '{name}' foi baixado com sucesso."))
            self.download_worker.download_failed.connect(lambda msg: self.download_dialog.reject())
            self.download_worker.download_failed.connect(lambda msg: QMessageBox.critical(self, "Erro no Download", msg))

            # Atualiza o widget na lista após download
            def after_download(path, name):
                for i in range(self.parent_app.files_layout.count()):
                    item = self.parent_app.files_layout.itemAt(i)
                    widget = item.widget()
                    if hasattr(widget, "file_item") and widget.file_item.get("id") == self.current_file_item.get("id"):
                        widget.local_file_path = path
                        widget.file_item["path"] = path
                        break

            self.download_worker.download_finished.connect(after_download)

            # Cleanup seguro usando QTimer.singleShot
            def cleanup():
                self.download_thread.quit()
                self.download_thread.wait()
                self.download_worker.deleteLater()
                self.download_thread.deleteLater()
                self.download_thread = None
                self.download_worker = None

            self.download_worker.download_finished.connect(lambda *_: QTimer.singleShot(0, cleanup))
            self.download_worker.download_failed.connect(lambda *_: QTimer.singleShot(0, cleanup))

            self.download_thread.started.connect(self.download_worker.run)
            self.download_thread.start()

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)  # Define o cursor via código

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DriveFileGalleryApp()
    ex.show()
    sys.exit(app.exec())