import re
import unicodedata
import sqlite3
import time


class SearchEngine:
    def __init__(self, indexer):
        self.indexer = indexer
        self._paged_cache = {}

    def parse_search_query(self, search_term):
        filters = {}
        terms = []
        exclude_terms = []
        or_groups = []
        quoted = re.findall(r'"([^"]+)"', search_term)
        for q in quoted:
            terms.append(q)
        search_term = re.sub(r'"[^"]+"', '', search_term)
        if 'is:starred' in search_term:
            filters['is_starred'] = True
            search_term = search_term.replace('is:starred', '')
        match_before = re.search(
            r'createdbefore:(\d{4}-\d{2}-\d{2})', search_term)
        match_after = re.search(
            r'createdafter:(\d{4}-\d{2}-\d{2})', search_term)
        import datetime
        if match_before:
            filters['created_before'] = datetime.datetime.strptime(
                match_before.group(1), '%Y-%m-%d')
            search_term = search_term.replace(match_before.group(0), '')
        if match_after:
            filters['created_after'] = datetime.datetime.strptime(
                match_after.group(1), '%Y-%m-%d')
            search_term = search_term.replace(match_after.group(0), '')
        symbol_tag_pattern = r'([<&#@][\w\d]+)'
        symbol_tags = re.findall(symbol_tag_pattern, search_term)
        for tag in symbol_tags:
            terms.append(tag)
        search_term = re.sub(symbol_tag_pattern, '', search_term)
        exclude_terms += re.findall(r'-([\w<&#@][\w\d]+)', search_term)
        search_term = re.sub(r'-([\w<&#@][\w\d]+)', '', search_term)
        if ' or ' in search_term.lower():
            or_groups = [t.strip() for t in re.split(
                r'(?i)\s+or\s+', search_term) if t.strip()]
        elif ' and ' in search_term.lower():
            terms += [t.strip()
                      for t in re.split(r'(?i)\s+and\s+', search_term) if t.strip()]
        else:
            terms += [t for t in re.split(r'\s+', search_term) if t]
        terms = list(dict.fromkeys([t for t in terms if t]))
        exclude_terms = list(dict.fromkeys([t for t in exclude_terms if t]))
        return terms, exclude_terms, or_groups, filters

    def normalize_text(self, text):
        if not text:
            return ""
        allowed_symbols = {'<', '>', '&', '#', '@'}
        normalized = ''.join(
            c for c in unicodedata.normalize('NFD', text.lower().strip())
            if unicodedata.category(c) != 'Mn' or c in allowed_symbols
        )
        return normalized

    def remove_accents(self, text):
        return self.normalize_text(text)

    def get_search_suggestions(self, search_term, search_all_sources, limit=10):
        self.indexer.ensure_conn()
        self.indexer.cursor.execute("PRAGMA synchronous=OFF")

        quoted_term = search_term.strip().replace('"', '""')
        query_term = f'"{quoted_term}*"'

        if search_all_sources:
            query = "SELECT name FROM search_index WHERE search_index MATCH ? OR normalized_name MATCH ? OR normalized_description MATCH ? ORDER BY rank LIMIT ?"
            self.indexer.cursor.execute(
                query, (query_term, query_term, query_term, limit))
        else:
            query = "SELECT name FROM search_index WHERE (search_index MATCH ? OR normalized_name MATCH ? OR normalized_description MATCH ?) AND source = 'local' ORDER BY rank LIMIT ?"
            self.indexer.cursor.execute(
                query, (query_term, query_term, query_term, limit))

        suggestions = [row[0] for row in self.indexer.cursor.fetchall()]

        self.indexer.cursor.execute("PRAGMA synchronous=FULL")
        return list(dict.fromkeys(suggestions))

    def load_files_paged(self, source, page, page_size, search_term=None, sort_by='name_asc', filter_type='all', folder_id=None, advanced_filters=None, explorer_special=False):
        self.indexer.ensure_conn()
        if self.indexer.conn is None:
            return []
        cache_key = (source, page, page_size, search_term, sort_by,
                     filter_type, folder_id, str(advanced_filters), explorer_special)
        if cache_key in self._paged_cache:
            return self._paged_cache[cache_key]
        offset = page * page_size
        sort_map = {
            'name_asc': 'name ASC',
            'name_desc': 'name DESC',
            'size_asc': 'size ASC',
            'size_desc': 'size DESC',
            'created_desc': 'createdTime DESC',
            'created_asc': 'createdTime ASC'
        }
        order_by_clause = sort_map.get(sort_by, 'name ASC')
        files_where_clauses = []
        files_params = []
        if search_term:
            norm_search_term = self.normalize_text(search_term)
            print(
                f"Termo original: '{search_term}' -> Normalizado: '{norm_search_term}'")
            terms, exclude_terms, or_groups, extra_filters = self.parse_search_query(
                norm_search_term)

            def quote_if_short_or_symbol(term):
                return f'"{term}"' if len(term) <= 4 or re.match(r'^[<&#@]', term) else term
            valid_terms = [quote_if_short_or_symbol(t.strip()) for t in (or_groups if or_groups else terms) if t and not t.startswith(
                '-') and t.strip() and t.strip().upper() not in ['OR', 'AND']]
            if not valid_terms:
                self._paged_cache[cache_key] = []
                return []
            if or_groups:
                fts_query = ' OR '.join(valid_terms)
            else:
                fts_query = ' '.join(valid_terms)
            if exclude_terms:
                not_query = ' NOT '.join([f'"{t}"' for t in exclude_terms])
                fts_query += f" NOT {not_query}"
            if not fts_query.strip():
                self._paged_cache[cache_key] = []
                return []
            if explorer_special:
                query = f"SELECT DISTINCT file_id FROM search_index WHERE (search_index MATCH ? OR normalized_name MATCH ? OR normalized_description MATCH ?) AND source = 'local' ORDER BY rank"
                params = (fts_query, fts_query, fts_query)
            else:
                query = f"SELECT DISTINCT file_id FROM search_index WHERE search_index MATCH ? OR normalized_name MATCH ? OR normalized_description MATCH ? ORDER BY rank"
                params = (fts_query, fts_query, fts_query)
            try:
                self.indexer.cursor.execute(query, params)
                file_ids_to_fetch = [row[0]
                                     for row in self.indexer.cursor.fetchall()]
                print(f"Resultados FTS: {file_ids_to_fetch}")
            except sqlite3.OperationalError as e:
                print(f"Erro na consulta FTS: {e}")
                print(f"Consulta problemática: {fts_query}")
                self._paged_cache[cache_key] = []
                return []
            if not file_ids_to_fetch:
                self._paged_cache[cache_key] = []
                return []
            placeholders = ','.join('?' for _ in file_ids_to_fetch)
            details_query = f"SELECT file_id, name, path, mimeType, source, description, thumbnailLink, thumbnailPath, size, modifiedTime, createdTime, parentId, starred FROM files WHERE file_id IN ({placeholders})"
            filter_clauses = []
            filter_params = list(file_ids_to_fetch)
            if extra_filters.get('is_starred'):
                filter_clauses.append("starred = 1")
            if extra_filters.get('created_before'):
                filter_clauses.append("createdTime <= ?")
                filter_params.append(
                    int(time.mktime(extra_filters['created_before'].timetuple())))
            if extra_filters.get('created_after'):
                filter_clauses.append("createdTime >= ?")
                filter_params.append(
                    int(time.mktime(extra_filters['created_after'].timetuple())))

            if advanced_filters:
                if advanced_filters.get('category'):
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
                                filter_params.append(f"%{ext}")
                            if ext_conditions:
                                filter_clauses.append(
                                    f"({' OR '.join(ext_conditions)})")

                if advanced_filters.get('extension'):
                    filter_clauses.append("name LIKE ?")
                    filter_params.append(f"%{advanced_filters['extension']}")
                    filter_clauses.append("mimeType != 'folder'")
                    filter_clauses.append(
                        "mimeType != 'application/vnd.google-apps.folder'")

                if advanced_filters.get('is_starred'):
                    filter_clauses.append("starred = 1")

                if advanced_filters.get('created_before'):
                    filter_clauses.append("createdTime <= ?")
                    filter_params.append(
                        int(time.mktime(advanced_filters['created_before'].timetuple())))

                if advanced_filters.get('created_after'):
                    filter_clauses.append("createdTime >= ?")
                    filter_params.append(
                        int(time.mktime(advanced_filters['created_after'].timetuple())))

            if filter_clauses:
                details_query += " AND " + " AND ".join(filter_clauses)
            self.indexer.cursor.execute(details_query, filter_params)
            rows = self.indexer.cursor.fetchall()
            result = self.indexer._build_file_objects_from_search(rows)
            if sort_by == 'name_asc':
                result = sorted(
                    result, key=lambda x: x.get('name', '').lower())
            elif sort_by == 'name_desc':
                result = sorted(result, key=lambda x: x.get(
                    'name', '').lower(), reverse=True)
            elif sort_by == 'created_desc':
                result = sorted(result, key=lambda x: x.get(
                    'createdTime', 0), reverse=True)
            elif sort_by == 'created_asc':
                result = sorted(result, key=lambda x: x.get('createdTime', 0))
            elif sort_by == 'modified_desc':
                result = sorted(result, key=lambda x: x.get(
                    'modifiedTime', 0), reverse=True)
            elif sort_by == 'modified_asc':
                result = sorted(result, key=lambda x: x.get('modifiedTime', 0))
            elif sort_by == 'size_asc':
                result = sorted(result, key=lambda x: x.get('size', 0))
            elif sort_by == 'size_desc':
                result = sorted(result, key=lambda x: x.get(
                    'size', 0), reverse=True)
            start = offset
            end = offset + page_size
            paged_result = result[start:end]
            self._paged_cache[cache_key] = paged_result
            return paged_result
        else:
            if source:
                files_where_clauses.append("source=?")
                files_params.append(source)
            if folder_id:
                files_where_clauses.append("parentId=?")
                files_params.append(folder_id)
            else:
                files_where_clauses.append(
                    "(parentId IS NULL OR parentId = '')")
            if filter_type == 'image':
                files_where_clauses.append("mimeType LIKE 'image/%'")
            elif filter_type == 'document':
                files_where_clauses.append(
                    "(mimeType LIKE 'application/vnd.google-apps.document' OR mimeType LIKE 'application/pdf' OR mimeType LIKE '%wordprocessingml.document%')")
            elif filter_type == 'spreadsheet':
                files_where_clauses.append(
                    "(mimeType LIKE 'application/vnd.google-apps.spreadsheet' OR mimeType LIKE '%spreadsheetml.sheet%')")
            elif filter_type == 'presentation':
                files_where_clauses.append(
                    "(mimeType LIKE 'application/vnd.google-apps.presentation' OR mimeType LIKE '%presentationml.presentation%')")
            elif filter_type == 'folder':
                files_where_clauses.append(
                    "mimeType = 'folder' OR mimeType = 'application/vnd.google-apps.folder'")
            if advanced_filters:
                if 'size_min' in advanced_filters and advanced_filters['size_min']:
                    files_where_clauses.append("size >= ?")
                    files_params.append(
                        advanced_filters['size_min'] * 1024 * 1024)
                if 'size_max' in advanced_filters and advanced_filters['size_max']:
                    files_where_clauses.append("size <= ?")
                    files_params.append(
                        advanced_filters['size_max'] * 1024 * 1024)
                if 'modified_after' in advanced_filters and advanced_filters['modified_after']:
                    files_where_clauses.append("modifiedTime >= ?")
                    files_params.append(
                        int(time.mktime(advanced_filters['modified_after'].timetuple())))
                if 'created_after' in advanced_filters and advanced_filters['created_after']:
                    files_where_clauses.append("createdTime >= ?")
                    files_params.append(
                        int(time.mktime(advanced_filters['created_after'].timetuple())))
                if 'created_before' in advanced_filters and advanced_filters['created_before']:
                    files_where_clauses.append("createdTime <= ?")
                    files_params.append(
                        int(time.mktime(advanced_filters['created_before'].timetuple())))
                if 'extension' in advanced_filters and advanced_filters['extension']:
                    files_where_clauses.append("name LIKE ?")
                    files_params.append(f"%{advanced_filters['extension']}")
                    files_where_clauses.append("mimeType != 'folder'")
                    files_where_clauses.append(
                        "mimeType != 'application/vnd.google-apps.folder'")
                if 'is_starred' in advanced_filters and advanced_filters['is_starred']:
                    files_where_clauses.append("starred = 1")
                if advanced_filters and advanced_filters.get('category'):
                    category = advanced_filters['category']
                    if category != '':
                        category_extensions = {
                            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff'],
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
                                files_params.append(f"%{ext}")
                            if ext_conditions:
                                files_where_clauses.append(
                                    f"({' OR '.join(ext_conditions)})")
            query = f"SELECT file_id, name, path, mimeType, source, description, thumbnailLink, thumbnailPath, size, modifiedTime, createdTime, parentId, starred FROM files WHERE {' AND '.join(files_where_clauses)} ORDER BY {order_by_clause} LIMIT ? OFFSET ?"
            if explorer_special:
                query = query.replace("WHERE", "WHERE source = 'local' AND")
            files_params.extend([page_size, offset])
            self.indexer.cursor.execute(query, files_params)
            rows = self.indexer.cursor.fetchall()
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
                    'createdTime': row[10],
                    'parentId': row[11],
                    'starred': bool(row[12])
                } for row in rows
            ]
            self._paged_cache[cache_key] = files
            return files

    def debug_search_normalization(self, search_term):
        if not search_term:
            print("\n⚠️ DEBUG: Nenhum termo de busca fornecido")
            return

        print(f"\n" + "="*60)
        print(f"🔍 DEBUG BUSCA NORMALIZADA - {search_term}")
        print(f"="*60)

        normalized = self.normalize_text(search_term)
        print(f"📝 Termo original: '{search_term}'")
        print(f"📝 Termo normalizado: '{normalized}'")
        print(
            f"📝 Mudança detectada: {'Sim' if search_term.lower() != normalized else 'Não'}")

        try:
            self.indexer.cursor.execute('SELECT COUNT(*) FROM search_index')
            total_indexed = self.indexer.cursor.fetchone()[0]
            print(f"💾 Total de arquivos no índice: {total_indexed:,}")
        except Exception as e:
            print(f"❌ Erro ao acessar índice: {e}")
            return

        print(f"\n🔍 TESTE 1: Busca com termo original")
        original_results = self.load_files_paged(
            source=None, page=0, page_size=8, search_term=search_term,
            sort_by='name_asc', filter_type='all'
        )
        print(f"   Resultados encontrados: {len(original_results)}")

        print(f"\n🔍 TESTE 2: Busca com termo normalizado")
        normalized_results = self.load_files_paged(
            source=None, page=0, page_size=8, search_term=normalized,
            sort_by='name_asc', filter_type='all'
        )
        print(f"   Resultados encontrados: {len(normalized_results)}")

        consistent = len(original_results) == len(normalized_results)
        status = "✅ CONSISTENTE" if consistent else "⚠️ INCONSISTENTE"
        print(f"\n🎯 STATUS DA NORMALIZAÇÃO: {status}")
        if original_results:
            print(f"\n📋 AMOSTRAS (máximo 5):")
            for i, result in enumerate(original_results[:5]):
                name = result.get('name', 'N/A')
                source = result.get('source', 'N/A')
                print(f"   {i+1}. [{source}] {name}")
        else:
            print(f"\n📋 Nenhum resultado encontrado")

        print(f"\n🔧 DEBUG AVANÇADO FTS5:")
        try:
            self.indexer.cursor.execute(
                'SELECT name FROM search_index WHERE search_index MATCH ? LIMIT 3',
                (f'"{normalized}"',)
            )
            fts_results = self.indexer.cursor.fetchall()
            print(
                f"   FTS5 direto com \"{normalized}\": {len(fts_results)} resultados")
            if normalized != search_term.lower():
                accent_pattern = f'%{search_term.lower()}%'
                self.indexer.cursor.execute(
                    'SELECT name FROM files WHERE LOWER(name) LIKE ? LIMIT 3',
                    (accent_pattern,)
                )
                accent_files = self.indexer.cursor.fetchall()
                print(
                    f"   Arquivos com acentos similares: {len(accent_files)}")
                for file in accent_files:
                    original_name = file[0]
                    normalized_name = self.normalize_text(original_name)
                    print(f"     '{original_name}' -> '{normalized_name}'")

        except Exception as e:
            print(f"   ❌ Erro no debug avançado: {e}")

        print(f"\n" + "="*60)
        print(f"💡 DICA: Use termos como 'formação', 'ação', 'coração' para testar")
        print(f"="*60)
