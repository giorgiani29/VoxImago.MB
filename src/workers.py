# workers.py - Workers e tarefas assíncronas do Vox Imago
# Inclui AuthWorker, ThumbnailWorker, DownloadWorker, LocalScanWorker, DriveSyncWorker.
# Use este arquivo para executar tarefas paralelas e assíncronas no aplicativo.

import sys
import time
import sqlite3
import requests
import os
import io
import os
import logging
from datetime import datetime, timezone
from .database import open_db_for_thread, normalize_text
from .thumbnails import ThumbnailCache
from googleapiclient.http import MediaIoBaseDownload
from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from .utils import find_local_matches

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='app.log',
    filemode='a'
)


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

THUMBNAIL_CACHE_DIR = "assets/thumbnail_cache"
CREDENTIALS_FILE = "config/credentials.json"
TOKEN_FILE = "config/token.json"


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
            creds = flow.run_local_server(
                port=0, access_type='offline', prompt='consent')

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
            cache_key = ThumbnailCache.get_thumbnail_cache_key(self.file_item)
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
        logging.info("DownloadWorker iniciado para: %s",
                     self.file_item.get('name'))
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
            logging.error("Erro no download: %s", e)
        finally:
            pass


class LocalScanWorker(QObject):
    update_status_signal = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, db_name, scan_path, force_sync=False):
        super().__init__()
        self.db_name = db_name
        if isinstance(scan_path, str):
            self.scan_path = [scan_path]
        else:
            self.scan_path = scan_path
        self.is_running = True
        self.force_sync = force_sync
        self.total_processed = 0
        self.progress_file = 'data/scan_progress.txt'
        self.conn = sqlite3.connect(self.db_name, timeout=30.0)

    def run(self):
        logging.debug(f"scan_path = {self.scan_path}")
        self.update_status_signal.emit("Escaneando arquivos locais...")
        last_sync_time = self.get_last_sync_time()
        try:
            last_sync_datetime = datetime.fromisoformat(
                last_sync_time[:-1] + '+00:00')
        except ValueError:
            logging.error(
                f"Erro: last_sync_time '{last_sync_time}' não está no formato esperado.")
            last_sync_datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)

        last_root = self.load_resume_point()
        logging.debug(f"last_root = {last_root}")

        conn = open_db_for_thread(self.db_name)
        cursor = conn.cursor()

        found_file_ids = set()

        cursor.execute('''
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
        cursor.execute('''
                            CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                                name,
                                description,
                                normalized_name,
                                normalized_description,
                                file_id UNINDEXED,
                                source UNINDEXED,
                                tokenize="trigram"
                            )
                            ''')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_source ON files(source)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_parentId ON files(parentId)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_mimeType ON files(mimeType)')
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_files_starred ON files(starred)")
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_name ON files(name COLLATE NOCASE)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_modifiedTime ON files(modifiedTime)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_createdTime ON files(createdTime)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_size ON files(size)')

        cursor.execute("PRAGMA mmap_size=268435456")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA cache_size=5000")
        conn.commit()
        batch_files = []
        batch_search = []

        resumed = False
        total_processed = 0
        for scan_path in self.scan_path:
            logging.debug(f"Processing scan_path: {scan_path}")
            if not self.is_running:
                break
            for root, dirs, files in os.walk(scan_path):
                if not self.is_running:
                    break
                if last_root and not resumed:
                    if root < last_root:
                        continue
                    elif root == last_root:
                        resumed = True
                        logging.info(f"🔄 Retomando escaneamento de: {root}")
                    else:
                        resumed = True

                self.save_resume_point(root)
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    parent_id = '' if root == scan_path else os.path.dirname(
                        dir_path)
                    try:
                        modified = int(os.path.getmtime(dir_path))
                        created = int(os.path.getctime(dir_path))
                        data_mais_antiga = min(created, modified)
                        ano_caminho = extrair_ano_banco_imagens(dir_path)
                        if ano_caminho and ano_caminho < datetime.fromtimestamp(data_mais_antiga).year:
                            data_final = int(
                                datetime(ano_caminho, 1, 1, tzinfo=timezone.utc).timestamp())
                        else:
                            data_final = data_mais_antiga
                        if modified < 0:
                            logging.warning(
                                f"Aviso: Tempo de modificação negativo para {dir_path}")
                            continue
                        if not self.force_sync and isinstance(modified, (int, float)) and last_sync_datetime:
                            if modified < last_sync_datetime.timestamp():
                                continue
                    except (FileNotFoundError, PermissionError):
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
                        'createdTime': data_final,
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
                        normalize_text(dir_item['name']),
                        normalize_text(dir_item['description']),
                        dir_item['id'],
                        dir_item['source']
                    ))
                    if len(batch_files) >= 100:
                        for attempt in range(3):
                            try:
                                cursor.executemany(
                                    "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch_files)
                                cursor.executemany(
                                    "INSERT OR REPLACE INTO search_index VALUES (?,?,?,?,?,?)", batch_search)
                                conn.commit()
                                break
                            except sqlite3.OperationalError as e:
                                if "database is locked" in str(e) and attempt < 2:
                                    time.sleep(1)
                                    continue
                                else:
                                    raise
                        batch_files.clear()
                        batch_search.clear()
                        self.total_processed += 100
                        self.progress_update.emit(self.total_processed)
                        logging.debug(
                            f"Processed batch of 100 dirs, total_processed now: {total_processed}")
                for name in files:
                    if not self.is_running:
                        break
                    if name.lower() == 'desktop.ini':
                        continue
                    file_path = os.path.join(root, name)
                    parent_id = '' if root == scan_path else os.path.dirname(
                        file_path)
                    try:
                        size = os.path.getsize(file_path)
                        modified = int(os.path.getmtime(file_path))
                        created = int(os.path.getctime(file_path))
                        data_mais_antiga = min(created, modified)
                        ano_caminho = extrair_ano_banco_imagens(file_path)
                        if ano_caminho and ano_caminho < datetime.fromtimestamp(data_mais_antiga).year:
                            data_final = int(
                                datetime(ano_caminho, 1, 1, tzinfo=timezone.utc).timestamp())
                        else:
                            data_final = data_mais_antiga
                        if modified < 0:
                            logging.warning(
                                "Aviso: Tempo de modificação negativo para %s", file_path)
                            continue
                        if not self.force_sync and isinstance(modified, (int, float)) and last_sync_datetime:
                            if modified < last_sync_datetime.timestamp():
                                continue
                    except (OSError, FileNotFoundError):
                        logging.error("Erro ao acessar %s: %s",
                                      file_path, sys.exc_info()[1])
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
                        'createdTime': data_final,
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
                        normalize_text(file_item['name']),
                        normalize_text(file_item['description']),
                        file_item['id'],
                        file_item['source']
                    ))
                    if len(batch_files) >= 100:
                        for attempt in range(3):
                            try:
                                cursor.executemany(
                                    "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch_files)
                                cursor.executemany(
                                    "INSERT OR REPLACE INTO search_index VALUES (?,?,?,?,?,?)", batch_search)
                                conn.commit()
                                break
                            except sqlite3.OperationalError as e:
                                if "database is locked" in str(e) and attempt < 2:
                                    time.sleep(1)
                                    continue
                                else:
                                    raise
                        batch_files.clear()
                        batch_search.clear()
                        self.total_processed += 100
                        self.progress_update.emit(self.total_processed)
        if batch_files:
            for attempt in range(3):
                try:
                    cursor.executemany(
                        "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch_files)
                    cursor.executemany(
                        "INSERT OR REPLACE INTO search_index VALUES (?,?,?,?,?,?)", batch_search)
                    conn.commit()
                    break
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < 2:
                        time.sleep(1)
                        continue
                    else:
                        raise
            self.total_processed += len(batch_files)
            self.progress_update.emit(self.total_processed)
        logging.info(
            f"Scan completed. Total items processed: {total_processed}")
        conn.close()
        self.finished.emit()
        self.update_last_sync_time()
        self.clear_resume_point()

    def load_resume_point(self):
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def save_resume_point(self, root):
        os.makedirs('data', exist_ok=True)
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            f.write(root)

    def clear_resume_point(self):
        try:
            os.remove(self.progress_file)
        except FileNotFoundError:
            pass

    def get_last_sync_time(self):
        if self.force_sync:
            logging.info(
                "🔄 Sincronização FORÇADA - ignorando cache de timestamp")
            return '1970-01-01T00:00:00.000Z'

        try:
            with open('data/last_local_sync.txt', 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return '1970-01-01T00:00:00.000Z'

    def update_last_sync_time(self):
        with open('data/last_local_sync.txt', 'w') as f:
            f.write(datetime.utcnow().isoformat() + 'Z')

    def stop(self):
        self.is_running = False


class DriveSyncWorker(QObject):
    sync_finished = pyqtSignal()
    sync_failed = pyqtSignal(str)
    update_status = pyqtSignal(str)
    progress_update = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, service, db_name='data/file_index.db', force_sync=False, selected_folders=None):
        super().__init__()
        self.service = service
        self.db_name = db_name
        self.is_running = True
        self.force_sync = force_sync
        self.selected_folders = selected_folders

    def terminate(self):
        self.is_running = False

    def run(self):
        sync_type = "FORÇADA" if self.force_sync else "incremental"
        logging.info(
            f"🔄 DriveSyncWorker.run() iniciado - Sincronização {sync_type}")
        status_msg = "Sincronização COMPLETA do Drive..." if self.force_sync else "Sincronizando arquivos e pastas do Drive..."
        self.update_status.emit(status_msg)
        self.progress_update.emit(0, status_msg)
        try:
            last_sync_time = self.get_last_sync_time()
            logging.info(f"📅 last_sync_time: {last_sync_time}")

            results = []
            page_token = None

            is_shared_drive_sync = False
            shared_drive_id = None

            if self.selected_folders and len(self.selected_folders) == 1:
                folder_id = self.selected_folders[0]
                if folder_id.startswith('0') and len(folder_id) > 10:
                    is_shared_drive_sync = True
                    shared_drive_id = folder_id
                    logging.info(
                        f"🏢 Detectado Shared Drive raiz: {shared_drive_id}")

            if is_shared_drive_sync:
                base_q = "trashed = false"
                if last_sync_time != '1970-01-01T00:00:00.000Z':
                    base_q += f" and modifiedTime > '{last_sync_time}'"

                logging.info(f"🔍 Query da API (Shared Drive): {base_q}")
                logging.info(
                    f"🏢 Usando corpora='drive', driveId='{shared_drive_id}'")

            else:
                base_q = "(trashed = false) or (sharedWithMe = true and trashed = false)"

                if self.selected_folders:
                    conditions = []
                    for folder_id in self.selected_folders:
                        if any(c.isalpha() for c in folder_id[:10]):
                            conditions.append(f"driveId = '{folder_id}'")
                        else:
                            conditions.append(f"'{folder_id}' in parents")

                    base_q += f" and ({' or '.join(conditions)})"
                    logging.info(
                        f"📁 Filtrando por pastas específicas: {self.selected_folders}")

                if last_sync_time != '1970-01-01T00:00:00.000Z':
                    base_q += f" and modifiedTime > '{last_sync_time}'"
                logging.info(f"🔍 Query da API: {base_q}")
            logging.info(f"🔐 Service disponível: {self.service is not None}")

            try:
                test_response = self.service.files().list(
                    q="trashed = false", pageSize=1).execute()
                test_files = test_response.get('files', [])
                logging.info(
                    f"✅ Teste API: {len(test_files)} arquivo(s) encontrado(s)")
                if test_files:
                    logging.info(
                        f"   Exemplo: {test_files[0].get('name', 'sem nome')}")
            except Exception as test_e:
                logging.error(f"❌ Erro no teste da API: {test_e}")
                raise test_e
            logging.info("🔄 Iniciando loop de busca de arquivos...")
            page_count = 0
            self.progress_update.emit(0, "Buscando arquivos do Drive...")
            while self.is_running:
                page_count += 1
                logging.info(
                    f"🔄 Buscando página {page_count}, page_token: {page_token}")

                if is_shared_drive_sync:
                    response = self.service.files().list(
                        q=base_q,
                        fields="nextPageToken, files(id, name, mimeType, description, parents, modifiedTime, createdTime, size, webViewLink, thumbnailLink)",
                        pageSize=1000,
                        pageToken=page_token,
                        corpora='drive',
                        driveId=shared_drive_id,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True
                    ).execute()
                else:
                    response = self.service.files().list(
                        q=base_q,
                        fields="nextPageToken, files(id, name, mimeType, description, parents, modifiedTime, createdTime, size, webViewLink, thumbnailLink)",
                        pageSize=1000,
                        pageToken=page_token,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True
                    ).execute()
                files = response.get('files', [])
                logging.info(f"📄 Recebidos {len(files)} arquivos nesta página")
                results.extend(files)
                page_token = response.get('nextPageToken', None)
                logging.info(f"📄 Próximo page_token: {page_token}")
                self.update_status.emit(
                    f"Buscando arquivos... página {page_count} (recebidos {len(files)})")
                self.progress_update.emit(
                    0, f"Buscando arquivos... página {page_count} (recebidos {len(files)})")
                if not page_token:
                    logging.info("🔚 Fim das páginas")
                    self.update_status.emit(
                        f"Busca finalizada. Total de arquivos recebidos: {len(results)}")
                    self.progress_update.emit(
                        0, f"Busca finalizada. Total de arquivos recebidos: {len(results)}")
                    break

            self.update_last_sync_time()

            if not self.is_running:
                return

            total_files = len(results)
            self.update_status.emit(
                f"Processando e salvando {total_files} arquivos do Drive em lotes...")
            self.progress_update.emit(
                0, f"Iniciando processamento em lotes...")

            conn = open_db_for_thread(self.db_name)
            from .database import FileIndexer
            indexer = FileIndexer(self.db_name)

            processed_items = []
            batch_to_save = []
            for i, file in enumerate(results):
                if not self.is_running:
                    conn.close()
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
                batch_to_save.append(item)

                if len(batch_to_save) >= 1000 or (i + 1) == total_files:
                    indexer.save_files_in_batch(batch_to_save, source='drive')
                    progress = int((i + 1) / total_files * 100)
                    status_msg = f"Salvando no banco: {i+1}/{total_files}"

                    self.update_status.emit(status_msg)
                    self.progress_update.emit(progress, status_msg)
                    logging.info(
                        f"Lote de {len(batch_to_save)} itens salvo no banco. Total processado: {i+1}")

                    batch_to_save.clear()
                    QCoreApplication.processEvents()

            if not self.is_running:
                conn.close()
                return

            matched_drive_ids = []
            fusion_count = 0
            debug_count = 0
            total_drive = len(processed_items)
            drive_with_size = 0
            match_count = 0

            fusion_start = time.time()
            logging.info("🔄 Iniciando processo de fusão de metadados...")
            self.update_status.emit(f"Iniciando fusão de metadados...")
            self.progress_update.emit(0, f"Iniciando fusão de metadados...")

            for i, drive_item in enumerate(processed_items):
                if drive_item['size'] > 0:
                    drive_with_size += 1

                if i % 100 == 0:
                    logging.info(
                        f"Fusão: {i}/{len(processed_items)} arquivos processados")
                    QCoreApplication.processEvents()
                    self.update_status.emit(
                        f"Fusão: {i}/{len(processed_items)} arquivos processados")
                    progress = int((i + 1) / total_drive *
                                   100) if total_drive else 0
                    self.progress_update.emit(
                        progress, f"Fusão: {i}/{total_drive} arquivos processados")

                match_start = time.time()
                matches = find_local_matches(drive_item, indexer.cursor)
                match_time = time.time() - match_start
                if i % 100 == 0:
                    logging.debug(
                        f"Tempo para matching do arquivo {i}: {match_time:.4f} segundos")

                local_rows = [(match,) for match in matches] if matches else []

                if matches and drive_item['size'] > 0:
                    if len(matches) > 1:
                        logging.warning(
                            f"⚠️ Conflito de metadados: Múltiplos matches ({len(matches)}) para arquivo Drive '{drive_item['name']}' (ID: {drive_item['id']})")
                    for local_row in local_rows:
                        local_id = local_row[0]
                        if match_count < 5:
                            logging.debug(
                                f"DEBUG: Match found for Drive file: {drive_item['name']} size: {drive_item['size']} -> local {local_id}")
                        indexer.cursor.execute(
                            "SELECT description FROM files WHERE file_id = ?", (local_id,))
                        local_desc = indexer.cursor.fetchone()
                        if local_desc and local_desc[0] and local_desc[0] != drive_item['description']:
                            logging.warning(
                                f"⚠️ Conflito de metadados: Descrição local diferente para '{drive_item['name']}' (local: '{local_desc[0][:50]}...', drive: '{drive_item['description'][:50]}...')")
                        try:
                            indexer.cursor.execute(
                                "UPDATE files SET description = ?, thumbnailLink = ?, webContentLink = ? WHERE file_id = ?",
                                (drive_item['description'], drive_item['thumbnailLink'],
                                 drive_item['webContentLink'], local_id)
                            )
                            indexer.cursor.execute(
                                "UPDATE search_index SET description = ?, normalized_description = ? WHERE file_id = ?",
                                (drive_item['description'], normalize_text(
                                    drive_item['description']), local_id)
                            )
                            fusion_count += 1
                        except Exception as e:
                            logging.error(
                                f"❌ Erro ao fusionar metadados para arquivo '{drive_item['name']}' (ID: {drive_item['id']}): {e}")
                        match_count += 1
                        if fusion_count % 1000 == 0 and fusion_count > 0:
                            indexer.conn.commit()
                            logging.info(
                                f"[LOG] Fusionados até agora: {fusion_count}")
                    matched_drive_ids.append(drive_item['id'])
                elif drive_item['size'] > 0:
                    logging.warning(
                        f"❌ Falha de fusão: Nenhum match encontrado para arquivo Drive '{drive_item['name']}' (tamanho: {drive_item['size']}, ID: {drive_item['id']})")

            logging.info(
                f"[LOG] Total Drive files: {total_drive}, with size >0: {drive_with_size}, matches: {match_count}")
            logging.info(f"[LOG] Total fusionados: {fusion_count}")

            self.update_status.emit(
                f"Fusão concluída. Total fusionados: {fusion_count}")
            self.progress_update.emit(
                100, f"Fusão concluída. Total fusionados: {fusion_count}")

            def delete_in_batches(cursor, table, id_list, batch_size=500):
                logging.info(
                    f"[LOG] Iniciando deletes em lote na tabela '{table}' ({len(id_list)} IDs, batch_size={batch_size})")
                for i in range(0, len(id_list), batch_size):
                    batch = id_list[i:i+batch_size]
                    logging.info(
                        f"[LOG] Deletando batch {i//batch_size+1}: {len(batch)} IDs na tabela '{table}'...")
                    placeholders = ','.join('?' for _ in batch)
                    sql = f"DELETE FROM {table} WHERE file_id IN ({placeholders})"
                    cursor.execute(sql, batch)
                logging.info(
                    f"[LOG] Deletes em lote finalizados na tabela '{table}'")

            if matched_drive_ids:
                logging.info(
                    f"[LOG] Iniciando deletes em lote para arquivos fusionados...")
                delete_in_batches(indexer.cursor, 'files', matched_drive_ids)
                delete_in_batches(
                    indexer.cursor, 'search_index', matched_drive_ids)
                logging.info(f"[LOG] Deletes em lote concluídos.")

            logging.info("[LOG] Commitando alterações no banco de dados...")
            indexer.conn.commit()
            logging.info("[LOG] Commit concluído.")
            fusion_end = time.time()
            logging.info(
                f"Fusão concluída em {fusion_end - fusion_start:.2f} segundos")

            conn.close()
            self.update_status.emit(
                f"Sincronização concluída: {len(processed_items)} arquivos/pastas. Fusionados: {len(matched_drive_ids)}. {'Incremental' if last_sync_time != '1970-01-01T00:00:00.000Z' else 'Completa'}.")
            self.sync_finished.emit()
        except Exception as e:
            self.sync_failed.emit(f"Erro na sincronização do Drive: {e}")
            logging.error(f"Erro detalhado: {e}")

    def get_last_sync_time(self):
        if self.force_sync:
            logging.info(
                "🔄 Sincronização FORÇADA - ignorando cache de timestamp")
            return '1970-01-01T00:00:00.000Z'

        try:
            with open('data/last_sync.txt', 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return '1970-01-01T00:00:00.000Z'

    def update_last_sync_time(self):
        with open('data/last_sync.txt', 'w') as f:
            f.write(datetime.utcnow().isoformat() + 'Z')


def extrair_ano_banco_imagens(path):
    partes = os.path.normpath(path).split(os.sep)
    try:
        idx = partes.index('Banco de Imagens')
        ano = int(partes[idx + 1])
        return ano
    except (ValueError, IndexError):
        return None
