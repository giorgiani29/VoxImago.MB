# workers.py - Workers e tarefas assíncronas do Vox Imago
# Inclui AuthWorker, ThumbnailWorker, DownloadWorker, LocalScanWorker, DriveSyncWorker.
# Use este arquivo para executar tarefas paralelas e assíncronas no aplicativo.

from utils import load_settings, save_settings
from datetime import datetime
from database import remove_accents
from database import open_db_for_thread
from utils import get_thumbnail_cache_key
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
import time
import sqlite3
import requests
import os
import io
import uuid
import mimetypes
from PyQt6.QtCore import QObject, pyqtSignal
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'


def _check_initial_auth(self):
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if not creds or not creds.valid or not creds.refresh_token or not creds.client_id or not creds.client_secret:
                raise ValueError("Token inválido ou incompleto.")
        except Exception:
            creds = None

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    self.creds = creds


EXPORT_MIME_TYPES = {
    'application/vnd.google-apps.document': 'application/pdf',
    'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.google-apps.presentation': 'application/pdf',
}

EXPORT_FILE_EXTENSIONS = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
}

THUMBNAIL_CACHE_DIR = "thumbnail_cache"
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


class AuthWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)
    authenticated = pyqtSignal(Credentials)
    auth_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        creds = None
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

        if not os.path.exists(CREDENTIALS_FILE):
            self.auth_failed.emit(
                f"Erro: Arquivo {CREDENTIALS_FILE} não encontrado. Por favor, adicione-o.")
            return

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

            self.authenticated.emit(creds)
        except Exception as e:
            self.auth_failed.emit(
                f"Erro de autenticação: {e}. Verifique seu arquivo credentials.json.")


class ThumbnailWorker(QObject):
    finished = pyqtSignal(bytes, str)

    def __init__(self, thumbnail_url, file_item, parent=None):
        super().__init__(parent)
        self.thumbnail_url = thumbnail_url
        self.file_item = file_item
        os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)

    def run(self):
        try:
            cache_key = get_thumbnail_cache_key(self.file_item)
            thumbnail_path = os.path.join(
                THUMBNAIL_CACHE_DIR, f"{cache_key}.jpg")
            if os.path.exists(thumbnail_path):
                with open(thumbnail_path, 'rb') as f:
                    data = f.read()
                self.finished.emit(data, thumbnail_path)
                return
            response = requests.get(self.thumbnail_url)
            if response.status_code == 200:
                with open(thumbnail_path, 'wb') as f:
                    f.write(response.content)
                self.finished.emit(response.content, thumbnail_path)
            else:
                self.finished.emit(b'', '')
        except Exception:
            self.finished.emit(b'', '')


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
            if mime_type in EXPORT_MIME_TYPES:
                export_mime = EXPORT_MIME_TYPES[mime_type]
                request = self.service.files().export_media(
                    fileId=file_id, mimeType=export_mime)
                file_extension = EXPORT_FILE_EXTENSIONS.get(
                    export_mime, '.pdf')
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
                        pass
        except Exception as e:
            print(f"Erro no download: {e}")
        finally:
            pass


class LocalScanWorker(QObject):
    update_status_signal = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, db_name, scan_path):
        super().__init__()
        self.db_name = db_name
        if isinstance(scan_path, str):
            self.scan_path = [scan_path]
        else:
            self.scan_path = scan_path
        self.is_running = True
        self.total_processed = 0
        self.conn = sqlite3.connect(self.db_name, timeout=30.0)

    def run(self):
        import os
        self.update_status_signal.emit("Escaneando arquivos locais...")
        conn = open_db_for_thread(self.db_name)
        cursor = conn.cursor()
        batch_files = []
        batch_search = []
        for scan_path in self.scan_path:
            if not self.is_running:
                break
            for root, dirs, files in os.walk(scan_path):
                if not self.is_running:
                    break
                for name in dirs:
                    if not self.is_running:
                        break
                    dir_path = os.path.join(root, name)
                    parent_id = '' if root == scan_path else os.path.dirname(
                        dir_path)
                    try:
                        modified = int(os.path.getmtime(dir_path))
                        created = int(os.path.getctime(dir_path))
                    except FileNotFoundError:
                        continue
                    dir_item = {
                        'id': dir_path,
                        'name': name,
                        'path': dir_path,
                        'mimeType': 'folder',
                        'source': 'local',
                        'description': '',
                        'thumbnailLink': '',
                        'thumbnailPath': '',
                        'size': 0,
                        'modifiedTime': modified,
                        'createdTime': created,
                        'parentId': parent_id,
                    }
                    batch_files.append((
                        dir_item['id'],
                        dir_item['name'],
                        dir_item['path'],
                        dir_item['mimeType'],
                        dir_item['source'],
                        dir_item['description'],
                        dir_item['thumbnailLink'],
                        dir_item['thumbnailPath'],
                        dir_item['size'],
                        dir_item['modifiedTime'],
                        dir_item['createdTime'],
                        dir_item['parentId'],
                        None,
                        0
                    ))
                    batch_search.append((
                        dir_item['name'],
                        dir_item['description'],
                        dir_item['id'],
                        dir_item['source']
                    ))
                    if len(batch_files) >= 100:
                        cursor.executemany(
                            "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch_files)
                        cursor.executemany(
                            "INSERT OR REPLACE INTO search_index VALUES (?,?,?,?)", batch_search)
                        conn.commit()
                        batch_files.clear()
                        batch_search.clear()
                        self.total_processed += 100
                        self.progress_update.emit(self.total_processed)
                for name in files:
                    if not self.is_running:
                        break
                    file_path = os.path.join(root, name)
                    parent_id = '' if root == scan_path else os.path.dirname(
                        file_path)
                    try:
                        size = os.path.getsize(file_path)
                        modified = int(os.path.getmtime(file_path))
                        created = int(os.path.getctime(file_path))
                    except FileNotFoundError:
                        continue
                    file_item = {
                        'id': file_path,
                        'name': name,
                        'path': file_path,
                        'mimeType': 'file',
                        'source': 'local',
                        'description': '',
                        'thumbnailLink': '',
                        'thumbnailPath': '',
                        'size': size,
                        'modifiedTime': modified,
                        'createdTime': created,
                        'parentId': parent_id,
                    }
                    batch_files.append((
                        file_item['id'],
                        file_item['name'],
                        file_item['path'],
                        file_item['mimeType'],
                        file_item['source'],
                        file_item['description'],
                        file_item['thumbnailLink'],
                        file_item['thumbnailPath'],
                        file_item['size'],
                        file_item['modifiedTime'],
                        file_item['createdTime'],
                        file_item['parentId'],
                        None,
                        0
                    ))
                    batch_search.append((
                        file_item['name'],
                        file_item['description'],
                        file_item['id'],
                        file_item['source']
                    ))
                    if len(batch_files) >= 100:
                        cursor.executemany(
                            "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch_files)
                        cursor.executemany(
                            "INSERT OR REPLACE INTO search_index VALUES (?,?,?,?)", batch_search)
                        conn.commit()
                        batch_files.clear()
                        batch_search.clear()
                        self.total_processed += 100
                        self.progress_update.emit(self.total_processed)
        if batch_files:
            cursor.executemany(
                "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch_files)
            cursor.executemany(
                "INSERT OR REPLACE INTO search_index VALUES (?,?,?,?)", batch_search)
            conn.commit()
            self.total_processed += len(batch_files)
            self.progress_update.emit(self.total_processed)
        conn.close()
        self.finished.emit()

    def stop(self):
        self.is_running = False


class DriveSyncWorker(QObject):
    sync_finished = pyqtSignal()
    sync_failed = pyqtSignal(str)
    update_status = pyqtSignal(str)
    progress_update = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, service, db_name='file_index.db'):
        super().__init__()
        self.service = service
        self.db_name = db_name
        self.is_running = True

    def terminate(self):
        self.is_running = False

    def run(self):
        self.update_status.emit("Sincronizando arquivos e pastas do Drive...")
        try:
            results = []
            page_token = None
            while self.is_running:
                response = self.service.files().list(
                    q="trashed = false",
                    fields="nextPageToken, files(id, name, mimeType, description, parents, modifiedTime, createdTime, size, webViewLink, thumbnailLink)",
                    pageSize=1000,
                    pageToken=page_token
                ).execute()
                files = response.get('files', [])
                results.extend(files)
                page_token = response.get('nextPageToken', None)
                if not page_token:
                    break

            if not self.is_running:
                return

            total_files = len(results)
            processed_items = []
            for i, file in enumerate(results):
                if not self.is_running:
                    return
                item = {
                    'id': file.get('id'),
                    'name': file.get('name'),
                    'mimeType': file.get('mimeType'),
                    'source': 'drive',
                    'description': file.get('description', ''),
                    'thumbnailLink': file.get('thumbnailLink', ''),
                    'thumbnailPath': '',
                    'size': int(file.get('size', 0)) if file.get('size') else 0,
                    'modifiedTime': int(datetime.strptime(file.get('modifiedTime'), "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()) if file.get('modifiedTime') else 0,
                    'createdTime': int(datetime.strptime(file.get('createdTime'), "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()) if file.get('createdTime') else 0,
                    'parentId': file.get('parents', [''])[0] if file.get('parents') else '',
                    'path': None,
                    'webContentLink': file.get('webViewLink', ''),
                }
                processed_items.append(item)

                progress = int((i + 1) / total_files * 100)
                self.progress_update.emit(
                    progress, f"Sincronizando {file['name']}...")

            if not self.is_running:
                return

            conn = open_db_for_thread(self.db_name)
            from database import FileIndexer
            indexer = FileIndexer(self.db_name)
            indexer.save_files_in_batch(processed_items, source='drive')

            local_files = indexer.load_files_paged(
                source='local', page=0, page_size=10000, search_term=None)
            for drive_item in processed_items:
                for local_item in local_files:
                    if (local_item['name'] == drive_item['name'] and
                        local_item['size'] == drive_item['size'] and
                            local_item['size'] > 0):
                        indexer.cursor.execute(
                            "UPDATE files SET description = ? WHERE file_id = ?",
                            (drive_item['description'], local_item['id'])
                        )
                        indexer.cursor.execute(
                            "UPDATE search_index SET description = ? WHERE file_id = ?",
                            (remove_accents(
                                drive_item['description'].lower()), local_item['id'])
                        )
                        indexer.conn.commit()

            conn.close()
            self.update_status.emit(
                f"Sincronização concluída: {len(processed_items)} arquivos/pastas.")
            self.sync_finished.emit()
        except Exception as e:
            self.sync_failed.emit(f"Erro na sincronização do Drive: {e}")
