# database.py - Banco de dados do Vox Imago
# Contém a classe FileIndexer para manipulação do banco SQLite filtros e favoritos.
# Use este arquivo para acessar e gerenciar os dados do aplicativo.

import unicodedata
import sqlite3
from .search import SearchEngine
import os
import time
import shutil
import mimetypes

THUMBNAIL_CACHE_DIR = "thumbnail_cache"


class FileIndexer:

    def buscar_drive_por_metadados(self, termo):
        query = "SELECT file_id, name, path, description, starred, mimeType, createdTime FROM files WHERE source = 'drive' AND (name LIKE ? OR description LIKE ?)"
        like_term = f"%{termo}%"
        self.cursor.execute(query, (like_term, like_term))
        resultados = []
        for row in self.cursor.fetchall():
            arquivo = {
                'id': row[0],
                'name': row[1],
                'local_path': row[2],
                'description': row[3],
                'starred': bool(row[4]),
                'mimeType': row[5],
                'createdTime': row[6],
            }
            arquivo['is_local'] = os.path.exists(
                arquivo['local_path']) if arquivo['local_path'] else False
            resultados.append(arquivo)
        return resultados

    def __init__(self, db_name='data/file_index.db'):
        self.db_name = db_name
        db_dir = os.path.dirname(self.db_name)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"📁 Pasta '{db_dir}' criada automaticamente")
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()
        self._count_cache = {}
        self._paged_cache = {}
        self._auto_rebuild_search_index()

    def _auto_rebuild_search_index(self):
        try:
            self.cursor.execute("PRAGMA table_info(search_index)")
            columns = [row[1] for row in self.cursor.fetchall()]
            expected = {'name', 'description', 'normalized_name',
                        'normalized_description', 'file_id', 'source'}
            if not expected.issubset(set(columns)):
                print(
                    "🔄 Recriando índice de busca para compatibilidade com busca híbrida...")
                self.rebuild_search_index_with_normalization()
        except Exception as e:
            print(f"⚠️ Erro ao verificar/recriar índice de busca: {e}")

    def ensure_conn(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
        try:
            self.cursor.execute("SELECT 1")
        except sqlite3.ProgrammingError as e:
            if "closed" in str(e):
                self.conn = sqlite3.connect(self.db_name)
                self.cursor = self.conn.cursor()

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
                                normalized_name,
                                normalized_description,
                                file_id UNINDEXED,
                                source UNINDEXED,
                                tokenize="trigram"
                            )
                            ''')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_source ON files(source)')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_parentId ON files(parentId)')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_mimeType ON files(mimeType)')
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_files_starred ON files(starred)")
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_name ON files(name COLLATE NOCASE)')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_modifiedTime ON files(modifiedTime)')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_createdTime ON files(createdTime)')
        self.cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_files_size ON files(size)')

        self.cursor.execute("PRAGMA mmap_size=268435456")
        self.cursor.execute("PRAGMA journal_mode=WAL")
        self.cursor.execute("PRAGMA synchronous=NORMAL")
        self.cursor.execute("PRAGMA temp_store=MEMORY")
        self.cursor.execute("PRAGMA cache_size=5000")
        self.conn.commit()
        print("índice de resultados com trigram criado")

    def save_files_in_batch(self, files_list, source, simulate_error=False):
        self.ensure_conn()
        try:
            with self.conn:
                file_ids = [(item.get('id'),) for item in files_list]
                self.cursor.executemany(
                    "DELETE FROM files WHERE file_id = ?", file_ids)

                self.cursor.executemany(
                    "DELETE FROM search_index WHERE file_id = ?", file_ids)

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
                        item.get('size', 0),
                        item.get('modifiedTime'),
                        item.get('createdTime'),
                        item.get('parentId'),
                        item.get('webContentLink'),
                        0
                    ) for item in files_list
                ]
                self.cursor.executemany(
                    "INSERT OR REPLACE INTO files VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data_files)

                data_search_index = [
                    (
                        item.get('name', ''),
                        item.get('description', ''),
                        SearchEngine(None).normalize_text(
                            item.get('name', '')),
                        SearchEngine(None).normalize_text(
                            item.get('description', '')),
                        item.get('id'),
                        item.get('source')
                    ) for item in files_list
                ]
                self.cursor.executemany(
                    "INSERT OR REPLACE INTO search_index VALUES (?, ?, ?, ?, ?, ?)", data_search_index)

                if simulate_error:
                    raise ValueError("Simulating an error for rollback")

        except Exception as e:
            print(f"Erro ao salvar arquivos em lote, rollback acionado: {e}")
            raise

    def clear_cache(self):
        self.ensure_conn()
        if os.path.exists(THUMBNAIL_CACHE_DIR):
            shutil.rmtree(THUMBNAIL_CACHE_DIR)
        os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)
        self.cursor.execute(
            "UPDATE files SET thumbnailPath = NULL WHERE source = 'drive'")
        self.conn.commit()

    def count_files(self, source, search_term=None, filter_type=None, folder_id=None, advanced_filters=None):
        self.ensure_conn()
        cache_key = (source, search_term, filter_type,
                     folder_id, str(advanced_filters))
        if cache_key in self._count_cache:
            return self._count_cache[cache_key]
        params = []
        where_clauses = []
        file_ids = None
        if search_term:
            quoted_search_term = search_term.strip().replace('"', '""')
            query_term = f'"{quoted_search_term}*"'
            query = "SELECT DISTINCT file_id FROM search_index WHERE search_index MATCH ?"
            self.cursor.execute(query, (query_term,))
            file_ids = [row[0] for row in self.cursor.fetchall()]
            if not file_ids:
                self._count_cache[cache_key] = 0
                return 0
        if file_ids is not None:
            placeholders = ','.join('?' for _ in file_ids)
            where_clauses.append(f"file_id IN ({placeholders})")
            params.extend(file_ids)
        if source:
            where_clauses.append("source=?")
            params.append(source)
        if folder_id:
            where_clauses.append("parentId=?")
            params.append(folder_id)
        elif not search_term:
            where_clauses.append("(parentId IS NULL OR parentId = '')")
        if filter_type == 'image':
            where_clauses.append("mimeType LIKE 'image/%'")
        elif filter_type == 'document':
            where_clauses.append(
                "(mimeType LIKE 'application/vnd.google-apps.document' OR mimeType LIKE 'application/pdf' OR mimeType LIKE '%wordprocessingml.document%')")
        elif filter_type == 'spreadsheet':
            where_clauses.append(
                "(mimeType LIKE 'application/vnd.google-apps.spreadsheet' OR mimeType LIKE '%spreadsheetml.sheet%')")
        elif filter_type == 'presentation':
            where_clauses.append(
                "(mimeType LIKE 'application/vnd.google-apps.presentation' OR mimeType LIKE '%presentationml.presentation%')")
        elif filter_type == 'folder':
            where_clauses.append(
                "mimeType = 'folder' OR mimeType = 'application/vnd.google-apps.folder'")
        if advanced_filters:
            if 'size_min' in advanced_filters and advanced_filters['size_min']:
                where_clauses.append("size >= ?")
                params.append(advanced_filters['size_min'] * 1024 * 1024)
            if 'size_max' in advanced_filters and advanced_filters['size_max']:
                where_clauses.append("size <= ?")
                params.append(advanced_filters['size_max'] * 1024 * 1024)
            if 'modified_after' in advanced_filters and advanced_filters['modified_after']:
                where_clauses.append("modifiedTime >= ?")
                params.append(
                    int(time.mktime(advanced_filters['modified_after'].timetuple())))
            if 'created_after' in advanced_filters and advanced_filters['created_after']:
                where_clauses.append("createdTime >= ?")
                params.append(
                    int(time.mktime(advanced_filters['created_after'].timetuple())))
            if 'created_before' in advanced_filters and advanced_filters['created_before']:
                where_clauses.append("createdTime <= ?")
                params.append(
                    int(time.mktime(advanced_filters['created_before'].timetuple())))
            if 'extension' in advanced_filters and advanced_filters['extension']:
                where_clauses.append("name LIKE ?")
                params.append(f"%{advanced_filters['extension']}")
                where_clauses.append("mimeType != 'folder'")
                where_clauses.append(
                    "mimeType != 'application/vnd.google-apps.folder'")

            if 'category' in advanced_filters and advanced_filters['category']:
                category = advanced_filters['category']
                if category != '':
                    category_extensions = {
                        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff', '.heic', '.arw', '.cr2', '.nef', '.dng', '.raf', '.orf', '.srw'],
                        'videos': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v', '.3gp'],
                        'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
                        'audios': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
                        'others': []
                    }
                    if category in category_extensions and category != 'others':
                        extensions = category_extensions[category]
                        ext_conditions = []
                        for ext in extensions:
                            ext_conditions.append("name LIKE ?")
                            params.append(f"%{ext}")
                        if ext_conditions:
                            where_clauses.append(
                                f"({' OR '.join(ext_conditions)})")
        query = "SELECT COUNT(*) FROM files"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        self.cursor.execute(query, params)
        result = self.cursor.fetchone()[0]
        self._count_cache[cache_key] = result
        return result

    def get_file_count(self, source=None):
        self.ensure_conn()
        if source:
            self.cursor.execute(
                "SELECT COUNT(*) FROM files WHERE source = ?", (source,))
        else:
            self.cursor.execute("SELECT COUNT(*) FROM files")
        return self.cursor.fetchone()[0]

    def get_breadcrumb(self, folder_id, source):
        self.ensure_conn()
        if not folder_id:
            return [{'id': None, 'name': 'Root' if source == 'local' else 'Drive'}]

        breadcrumb = []
        current_id = folder_id
        while current_id:
            self.cursor.execute(
                "SELECT file_id, name, path, parentId FROM files WHERE file_id = ?", (current_id,))
            row = self.cursor.fetchone()
            if row:
                breadcrumb.append(
                    {'id': row[0], 'name': row[1], 'path': row[2]})
                current_id = row[3]
            else:
                break
        breadcrumb.append(
            {'id': None, 'name': 'Root' if source == 'local' else 'Drive'})
        return list(reversed(breadcrumb))

    def _build_file_objects_from_search(self, rows):
        files = []
        for row in rows:
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
                'createdTime': row[10],
                'parentId': row[11],
                'starred': bool(row[12]) if len(row) > 12 else False,
            }
            files.append(file)
        return files

    def set_starred(self, file_id, starred=True):
        self.ensure_conn()
        self.cursor.execute(
            "UPDATE files SET starred = ? WHERE file_id = ?", (1 if starred else 0, file_id))
        self.conn.commit()

    def rebuild_search_index_with_normalization(self):
        self.ensure_conn()

        try:
            print("🔄 Iniciando reconstrução do índice com normalização...")
            self.cursor.execute('DROP TABLE IF EXISTS search_index')
            self.cursor.execute('''
                    CREATE VIRTUAL TABLE search_index USING fts5(
                        name,
                        description,
                        normalized_name,
                        normalized_description,
                        file_id UNINDEXED,
                        source UNINDEXED,
                        tokenize="trigram"
                    )
                    ''')

            self.cursor.execute(
                'SELECT file_id, name, description, source FROM files')
            all_files = self.cursor.fetchall()

            print(f"📁 Processando {len(all_files)} arquivos existentes...")

            batch_data = []
            for i, (file_id, name, description, source) in enumerate(all_files):
                name = name or ""
                description = description or ""

                batch_data.append((
                    name,
                    description,
                    SearchEngine(None).normalize_text(name),
                    SearchEngine(None).normalize_text(description),
                    file_id,
                    source
                ))

                if len(batch_data) >= 1000:
                    self.cursor.executemany(
                        "INSERT INTO search_index VALUES (?, ?, ?, ?, ?, ?)",
                        batch_data
                    )
                    batch_data = []
                    print(
                        f"  📊 Processados {i + 1}/{len(all_files)} arquivos...")

            if batch_data:
                self.cursor.executemany(
                    "INSERT INTO search_index VALUES (?, ?, ?, ?, ?, ?)",
                    batch_data
                )

            self.conn.commit()
            print("✅ Índice reconstruído com sucesso!")

        except Exception as e:
            print(f"❌ Erro ao reconstruir o índice: {e}")
            self.conn.rollback()
            raise

    def close(self):
        self.conn.close()

    def add_file(self, file_path, source):
        if not os.path.exists(file_path):
            return
        file_id = file_path
        name = os.path.basename(file_path)
        path = file_path
        mimeType = mimetypes.guess_type(
            file_path)[0] or 'application/octet-stream'
        description = ''
        thumbnailLink = ''
        thumbnailPath = ''
        size = os.path.getsize(file_path)
        modifiedTime = int(os.path.getmtime(file_path))
        createdTime = int(os.path.getctime(file_path))
        parentId = ''
        webContentLink = None
        starred = 0
        self.ensure_conn()
        self.cursor.execute('''
            INSERT OR REPLACE INTO files (file_id, name, path, mimeType, source, description, thumbnailLink, thumbnailPath, size, modifiedTime, createdTime, parentId, webContentLink, starred)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (file_id, name, path, mimeType, source, description, thumbnailLink, thumbnailPath, size, modifiedTime, createdTime, parentId, webContentLink, starred))
        self.conn.commit()
        self.cursor.execute('INSERT OR REPLACE INTO search_index (name, description, normalized_name, normalized_description, file_id, source) VALUES (?, ?, ?, ?, ?, ?)',
                            (name, description, SearchEngine(None).normalize_text(name), SearchEngine(None).normalize_text(description), file_id, source))
        self.conn.commit()

    def toggle_starred(self, file_id):
        self.ensure_conn()
        self.cursor.execute(
            "SELECT starred FROM files WHERE file_id = ?", (file_id,))
        row = self.cursor.fetchone()
        if row:
            current = row[0]
            new_status = 0 if current else 1
            self.cursor.execute(
                "UPDATE files SET starred = ? WHERE file_id = ?", (new_status, file_id))
            self.conn.commit()
            return new_status
        return None


def open_db_for_thread(db_name):
    import sqlite3
    conn = sqlite3.connect(db_name, check_same_thread=False, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = 5000;")
    return conn
