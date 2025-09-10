# workers.py - Workers e tarefas assíncronas do Vox Imago
# Inclui AuthWorker, ThumbnailWorker, DownloadWorker, LocalScanWorker, DriveSyncWorker.
# Use este arquivo para executar tarefas paralelas e assíncronas no aplicativo.

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
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
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

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

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

        fields = "nextPageToken, files(id, name, mimeType, thumbnailLink, webViewLink, webContentLink, description, size, parents, modifiedTime, createdTime)"
        files_fetched = 0

        try:
            page_token = None
            while True:
                print("Buscando arquivos do Drive (meus e compartilhados)...")
                response = self.service.files().list(
                    fields=fields,
                    pageToken=page_token,
                    pageSize=1000,
                    corpora="user",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    q="trashed=false"
                ).execute()
                print(f"Página recebida, arquivos: {len(response.get('files', []))}")
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

            page_token = None
            while True:
                print("Buscando arquivos compartilhados comigo...")
                response = self.service.files().list(
                    fields=fields,
                    pageToken=page_token,
                    pageSize=1000,
                    corpora="user",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    q="sharedWithMe and trashed=false"
                ).execute()
                print(f"Página recebida (sharedWithMe), arquivos: {len(response.get('files', []))}")
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