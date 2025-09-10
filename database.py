# database.py - Banco de dados do Vox Imago
# Contém a classe FileIndexer para manipulação do banco SQLite, busca, filtros e favoritos.
# Use este arquivo para acessar e gerenciar os dados do aplicativo.

import sqlite3
import os
import time
import re
import shutil

THUMBNAIL_CACHE_DIR = "thumbnail_cache"

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
                params.append(advanced_filters['size_min'] * 1024 * 1024)
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
            quoted_phrases = re.findall(r'"([^"]+)"', search_term)
            search_term_no_quotes = re.sub(r'"[^"]+"', '', search_term)
            or_groups = [grp.strip() for grp in re.split(r'\s+OR\s+', search_term_no_quotes, flags=re.IGNORECASE) if grp.strip()]
            file_ids_to_fetch = set()
            ranks = []

            for group in or_groups:
                terms = [t.strip() for t in re.split(r'\s+', group) if t.strip()]
                positive_terms = [t for t in terms if not t.startswith('-')]
                negative_terms = [t[1:] for t in terms if t.startswith('-') and len(t) > 1]
                quoted_phrases_group = re.findall(r'"([^"]+)"', group)

                fts_clauses = []
                fts_params = []

                for phrase in quoted_phrases_group:
                    fts_clauses.append("search_index MATCH ?")
                    fts_params.append(f'"{phrase}"')

                if positive_terms:
                    pos_terms = [f'"{t.replace("\"", "\"\"")}"*' for t in positive_terms]
                    pos_query = ' '.join(pos_terms)
                    fts_clauses.append("search_index MATCH ?")
                    fts_params.append(pos_query)
                elif not quoted_phrases_group:
                    fts_clauses.append("1=1")

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
