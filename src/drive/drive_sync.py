"""
Módulo drive_sync

Este módulo gerencia a sincronização entre arquivos locais e o Google Drive no VoxImago.MB.
Inclui funções e classes para detectar alterações, transferir arquivos, resolver conflitos,
atualizar metadados e garantir a consistência entre o armazenamento local e a nuvem.
"""

import os
import time
import logging
from datetime import datetime
from src.database.database import open_db_for_thread, FileIndexer
from src.database.search import SearchEngine
from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication
from src.drive.match import find_local_matches
from .drive_service import DriveService


class DriveSync(QObject):
    sync_finished = pyqtSignal()
    sync_failed = pyqtSignal(str)
    update_status = pyqtSignal(str)
    progress_update = pyqtSignal(int, str)
    total_files_found = pyqtSignal(int)
    finished = pyqtSignal()
    metadata_fusion_completed = pyqtSignal(int)

    def __init__(self, service, db_name='data/file_index.db', selected_folders=None):
        super().__init__()
        self.service = service
        self.drive_service = DriveService(service)
        self.db_name = db_name
        self.is_running = True
        self.selected_folders = selected_folders
        self._sync_completed = False
        self._sync_failed = False

    def terminate(self):
        self.is_running = False

    def _emit_finish_signal(self, success=True, error_msg=None):
        if self._sync_completed or self._sync_failed:
            logging.info(
                f"🔄 Sinal já emitido anteriormente - ignorando duplicata")
            return

        if success:
            self._sync_completed = True
            logging.info("✅ ESTADO: Emitindo sync_finished")
            self.sync_finished.emit()
        else:
            self._sync_failed = True
            logging.info(f"❌ ESTADO: Emitindo sync_failed: {error_msg}")
            self.sync_failed.emit(error_msg or "Erro desconhecido")

    def _get_all_subfolders_recursive(self, folder_id, shared_drive_id=None):
        if not self.is_running:
            return [folder_id]
        return self.drive_service.get_all_subfolders_recursive(folder_id, shared_drive_id)

    def _count_total_files(self, base_q, is_shared_drive_sync, shared_drive_id, recursive_folders=None, specific_folder_filter=None):
        if not self.is_running:
            return 0

        logging.info(
            f"🔢 Delegando contagem para DriveService com query: {base_q}")
        self.update_status.emit("Contando arquivos no Drive...")

        try:
            if recursive_folders and specific_folder_filter:
                total = self.drive_service.count_files_in_folders(
                    recursive_folders, shared_drive_id
                )
            else:
                total = 0
                page_token = None
                max_pages = 200

                for page_count in range(1, max_pages + 1):
                    if not self.is_running:
                        break

                    try:
                        response = self.drive_service.list_files_paginated(
                            base_q=base_q,
                            is_shared_drive_sync=is_shared_drive_sync,
                            shared_drive_id=shared_drive_id,
                            page_token=page_token,
                            page_size=1000,
                            recursive_folders=recursive_folders,
                            fields_override="nextPageToken, files(id, parents)" if specific_folder_filter else "nextPageToken, files(id)"
                        )

                        files_page = response.get('files', [])

                        if specific_folder_filter and recursive_folders:
                            filtered_files = []
                            for file in files_page:
                                file_parent = file.get('parents', [''])[
                                    0] if file.get('parents') else ''
                                if file_parent in recursive_folders:
                                    filtered_files.append(file)
                            files_page = filtered_files

                        page_count_files = len(files_page)
                        total += page_count_files

                        if total % 5000 == 0 or page_count_files < 1000:
                            status_msg = f"Contados {total:,} arquivos no Drive..."
                            self.update_status.emit(status_msg)
                            logging.info(f"📢 {status_msg}")

                        page_token = response.get('nextPageToken', None)
                        if not page_token or not files_page:
                            break

                    except Exception as e:
                        logging.error(f"❌ Erro na página {page_count}: {e}")
                        if page_count >= 5:  # Após 5 tentativas, para
                            break
                        time.sleep(2)

            final_msg = f"Contagem finalizada: {total:,} arquivos"
            self.update_status.emit(final_msg)
            logging.info(f"✅ {final_msg}")
            return total

        except Exception as e:
            logging.error(f"❌ Erro na contagem: {e}")
            self.update_status.emit("Erro na contagem de arquivos")
            return 0

    def run(self):
        try:
            sync_start_time = time.perf_counter()
            logging.info(
                "🔄 [DRIVE SYNC] Iniciado - Sincronização COMPLETA com algoritmo otimizado")
            logging.info(
                f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            if not self.is_running:
                print("🛑 Sync cancelado antes de iniciar")
                self.sync_failed.emit("Cancelado antes de iniciar")
                return

            status_msg = "Sincronização COMPLETA do Drive..."
            self.update_status.emit(status_msg)
            self.progress_update.emit(0, status_msg)

        except Exception as e:
            error_msg = f"Erro crítico na inicialização: {str(e)}"
            print(f"🚨 {error_msg}")
            logging.error(error_msg)
            self.sync_failed.emit(error_msg)
            return

        matching_stats = {
            'total_matches': 0,
            'exact_matches': 0,
            'normalized_matches': 0,
            'aggressive_matches': 0,
            'similarity_matches': 0,
            'no_matches': 0,
            'total_matching_time': 0
        }

        try:

            page_token = None

            is_shared_drive_sync = False
            shared_drive_id = None

            recursive_folders = []
            specific_folder_filter = None

            if self.selected_folders and len(self.selected_folders) == 1:
                folder_id = self.selected_folders[0]
                if folder_id.startswith('0') and len(folder_id) > 15:
                    is_shared_drive_sync = True
                    shared_drive_id = folder_id
                    logging.info(
                        f"🏢 Detectado Shared Drive raiz: {shared_drive_id}")
                else:
                    logging.info(f"📁 Detectada pasta específica: {folder_id}")
                    from src.utils.utils import load_settings
                    settings = load_settings()
                    drive_folders = settings.get('drive_folders', [])
                    parent_shared_drive = None

                    for drive_folder in drive_folders:
                        if drive_folder.startswith('0') and len(drive_folder) > 15:
                            parent_shared_drive = drive_folder
                            break

                    if parent_shared_drive:
                        is_shared_drive_sync = True
                        shared_drive_id = parent_shared_drive
                        specific_folder_filter = folder_id
                        logging.info(
                            f"🚀 Usando API eficiente do Shared Drive {parent_shared_drive}")
                        logging.info(
                            f"🎯 Filtrando por pasta específica: {folder_id}")

                        recursive_folders = self._get_all_subfolders_recursive(
                            folder_id, parent_shared_drive)
                        logging.info(
                            f"📁 Encontradas {len(recursive_folders)} pastas para filtro")
                    else:
                        logging.warning(
                            "⚠️ Shared Drive pai não encontrado, usando método manual")
                        recursive_folders = self._get_all_subfolders_recursive(
                            folder_id, None)
                        logging.info(
                            f"📁 Encontradas {len(recursive_folders)} pastas para sincronização recursiva")

            if is_shared_drive_sync:
                base_q = "trashed = false"
                logging.info(f"🔍 Query da API (Shared Drive): {base_q}")
                logging.info(
                    f"🏢 Usando corpora='drive', driveId='{shared_drive_id}'")
            elif recursive_folders:
                base_q = "trashed = false"
                conditions = [
                    f"'{folder_id}' in parents" for folder_id in recursive_folders]
                base_q += f" and ({' or '.join(conditions)})"
                logging.info(
                    f"🔍 Query recursiva para {len(recursive_folders)} pastas: {base_q[:200]}...")
            else:
                base_q = "(trashed = false) or (sharedWithMe = true and trashed = false)"
                if self.selected_folders:
                    conditions = []
                    for folder_id in self.selected_folders:
                        if folder_id == 'root':
                            conditions.append("'root' in parents")
                        elif any(c.isalpha() for c in folder_id[:10]):
                            conditions.append(f"driveId = '{folder_id}'")
                        else:
                            conditions.append(f"'{folder_id}' in parents")
                    base_q += f" and ({' or '.join(conditions)})"
                    logging.info(
                        f"📁 Filtrando por pastas específicas: {self.selected_folders}")
                logging.info(f"🔍 Query da API: {base_q}")
            logging.info(f"🔐 Service disponível: {self.service is not None}")

            try:
                if not self.drive_service.test_api_connection():
                    raise Exception("Falha no teste de conexão com a API")
                logging.info("✅ Teste API: Conexão bem-sucedida")
            except Exception as test_e:
                logging.error(f"❌ Erro no teste da API: {test_e}")
                raise test_e
            logging.info("🔢 Iniciando contagem de arquivos no Drive...")
            try:
                total_files_in_drive = self._count_total_files(
                    base_q, is_shared_drive_sync, shared_drive_id, recursive_folders, specific_folder_filter)
                logging.info(
                    f"✅ Contagem concluída: {total_files_in_drive:,} arquivos")
            except Exception as count_error:
                logging.error(f"❌ Erro na contagem: {count_error}")
                total_files_in_drive = 0

            if not self.is_running:
                logging.info("🛑 Cancelado durante contagem")
                self._emit_finish_signal(
                    success=False, error_msg="Cancelado durante contagem")
                return

            self.total_files_found.emit(total_files_in_drive)
            logging.info(
                f"📊 Total de arquivos no Drive: {total_files_in_drive:,}")

            logging.info("🔄 Iniciando loop de busca de arquivos...")
            page_count = 0
            total_files_processed = 0
            fusion_count = 0
            max_pages = 300
            consecutive_errors = 0
            max_consecutive_errors = 10

            indexer = FileIndexer(self.db_name)

            if total_files_in_drive > 0:
                self.progress_update.emit(
                    0, f"Processando {total_files_in_drive:,} arquivos do Drive...")
            else:
                logging.warning("⚠️ Contagem falhou, usando modo estimativa")
                self.progress_update.emit(
                    0, "Processando arquivos do Drive (modo estimativa)...")

            PAGE_SIZE = 1000
            fusion_start_time = time.perf_counter()
            logging.info(
                f"🔄 [FUSÃO] Iniciando processo de fusão otimizado com índices")

            empty_pages_count = 0
            max_empty_pages = 3
            same_token_count = 0
            last_page_token = None

            while (self.is_running and
                   page_count < max_pages and
                   consecutive_errors < max_consecutive_errors and
                   empty_pages_count < max_empty_pages and
                   same_token_count < 5):

                page_count += 1
                page_start_time = time.perf_counter()

                if page_token == last_page_token and page_token is not None:
                    same_token_count += 1
                    logging.warning(
                        f"⚠️ Token repetido #{same_token_count}: {page_token}")
                    if same_token_count >= 5:
                        logging.error(
                            "🚨 Token repetido 5x - FORÇANDO SAÍDA para evitar loop infinito!")
                        break
                else:
                    same_token_count = 0

                last_page_token = page_token

                if page_count % 10 == 1:
                    logging.info(
                        f"🔄 Buscando página {page_count}, page_token: {page_token}")

                try:
                    response = self.drive_service.list_files_paginated(
                        base_q=base_q,
                        is_shared_drive_sync=is_shared_drive_sync,
                        shared_drive_id=shared_drive_id,
                        page_token=page_token,
                        page_size=PAGE_SIZE,
                        recursive_folders=recursive_folders
                    )
                    consecutive_errors = 0
                except Exception as api_error:
                    consecutive_errors += 1
                    logging.error(
                        f"❌ Erro na API do Google Drive (página {page_count}, tentativa {consecutive_errors}): {api_error}")
                    if consecutive_errors >= max_consecutive_errors:
                        logging.error(
                            "🚨 Muitos erros consecutivos na API, abortando sincronização")
                        break
                    time.sleep(min(consecutive_errors * 2, 10))
                    continue

                files_page = response.get('files', [])
                api_time = (time.perf_counter() - page_start_time) * 1000
                if page_count % 10 == 1:
                    logging.info(
                        f"📄 [PÁGINA {page_count}] {len(files_page)} arquivos | API: {api_time:.1f}ms")

                if not files_page:
                    empty_pages_count += 1
                    logging.info(
                        f"📭 Página vazia #{empty_pages_count}/{max_empty_pages}")
                    if empty_pages_count >= max_empty_pages:
                        logging.info(
                            "🔚 Muitas páginas vazias consecutivas - FINALIZANDO para evitar loop")
                        break
                else:
                    empty_pages_count = 0

                processed_items_page = []
                for idx, file in enumerate(files_page):
                    if specific_folder_filter and recursive_folders:
                        file_parent = file.get('parents', [''])[
                            0] if file.get('parents') else ''

                        selected_folder_ids = [
                            f for f in self.selected_folders if f != 'root']
                        if selected_folder_ids and 'root' not in self.selected_folders:
                            if file_parent not in recursive_folders:
                                continue

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
                    processed_items_page.append(item)
                    if (idx + 1) % 100 == 0 or (idx + 1) == len(files_page):
                        current_processed = total_files_processed + idx + 1
                        if total_files_in_drive > 0:
                            percent = min(
                                70, int(70 * current_processed / total_files_in_drive))
                        else:
                            percent = min(
                                70, int(70 * current_processed / max(1, 100000)))
                        self.progress_update.emit(
                            percent, f"Processando {current_processed:,}/{total_files_in_drive:,} arquivos...")
                        QCoreApplication.processEvents()

                if processed_items_page:
                    page_fusion_start = time.perf_counter()
                    page_fusion_count, matched_drive_ids = self.fuse_page_data(
                        processed_items_page, indexer)
                    fusion_count += page_fusion_count
                    page_fusion_time = (
                        time.perf_counter() - page_fusion_start) * 1000

                    unfused_items = [
                        item for item in processed_items_page if item['id'] not in matched_drive_ids]
                    if unfused_items:
                        indexer.save_files_in_batch(
                            unfused_items, source='drive')

                    total_files_processed += len(processed_items_page)
                    indexer.conn.commit()

                    if page_count % 10 == 1:
                        logging.info(
                            f"🔗 Página {page_count}: {page_fusion_count} fusões em {page_fusion_time:.1f}ms")

                status_msg = f"Processados {total_files_processed:,} arquivos | Fusionados: {fusion_count:,}"
                self.update_status.emit(status_msg)
                progress_percent = min(
                    90, int(70 + (20 * total_files_processed / max(total_files_in_drive, 1))))
                self.progress_update.emit(progress_percent, status_msg)

                page_token = response.get('nextPageToken', None)
                if not page_token:
                    if page_count % 10 == 1:
                        logging.info("🔚 Fim de todas as páginas.")
                    break

                QCoreApplication.processEvents()

            self.update_status.emit("Finalizando sincronização...")
            self.progress_update.emit(
                95, f"Finalização: {fusion_count:,} fusões realizadas")

            logging.info(
                f"🧹 Limpeza final: {fusion_count:,} fusões de metadados concluídas")

            self.metadata_fusion_completed.emit(fusion_count)

            logging.info(
                f"✅ Sincronização concluída. Total processado: {total_files_processed}, Total fusionado: {fusion_count}")
            self.update_status.emit(
                f"Sincronização concluída: {total_files_processed} arquivos. Fusionados: {fusion_count}.")
            self.progress_update.emit(100, "Sincronização concluída.")
            self._emit_finish_signal(success=True)
            if indexer:
                try:
                    indexer.close()
                except Exception:
                    pass
            self.finished.emit()

        except Exception as e:
            self._emit_finish_signal(
                success=False, error_msg=f"Erro na sincronização do Drive: {e}")
            logging.error(f"Erro detalhado: {e}", exc_info=True)
        finally:
            if not self._sync_completed and not self._sync_failed:
                if self.is_running:
                    logging.info("✅ FINALLY: Finalizando normalmente")
                    self._emit_finish_signal(success=True)
                else:
                    logging.info("🛑 FINALLY: Finalizando como cancelado")
                    self._emit_finish_signal(
                        success=False, error_msg="Cancelado pelo usuário")

    def fuse_page_data(self, page_items, indexer):
        fusion_count = 0
        matched_drive_ids = []

        valid_items = [
            item for item in page_items
            if item.get('size', 0) > 0 and
            (item.get('description') or item.get(
                'thumbnailLink') or item.get('webContentLink'))
        ]

        if not valid_items:
            return 0, []

        for drive_item in valid_items:
            try:
                matches = find_local_matches(drive_item, indexer.cursor)
                if matches:
                    for local_id in matches:
                        indexer.update_description(
                            local_id,
                            drive_item.get('description', ''),
                            drive_item.get('thumbnailLink', ''),
                            drive_item.get('webContentLink', ''),
                            commit=False,
                        )
                        fusion_count += 1
                    matched_drive_ids.append(drive_item['id'])
            except Exception as e:
                logging.warning(
                    f"⚠️ Fusão falhou para {drive_item.get('name', 'unknown')}: {str(e)[:100]}")
                continue

        return fusion_count, matched_drive_ids

    def fuse_all_data(self, indexer, batch_size=1000):
        cursor = indexer.cursor
        try:
            cursor.execute("SELECT COUNT(*) FROM files WHERE source='drive'")
            total_drive = cursor.fetchone()[0]
        except Exception:
            total_drive = 0

        processed = 0
        total_fusions = 0
        matched_to_delete = []

        offset = 0
        while True:
            cursor.execute(
                """
                SELECT file_id, name, size, description, thumbnailLink, webContentLink
                FROM files WHERE source='drive' LIMIT ? OFFSET ?
                """,
                (batch_size, offset)
            )
            rows = cursor.fetchall()
            if not rows:
                break

            for file_id, name, size, description, thumbnailLink, webContentLink in rows:
                drive_item = {
                    'id': file_id,
                    'name': name or '',
                    'size': size or 0,
                    'description': description or '',
                    'thumbnailLink': thumbnailLink or '',
                    'webContentLink': webContentLink or ''
                }
                matches = find_local_matches(drive_item, cursor)
                if matches:
                    for local_id in matches:
                        try:
                            indexer.update_description(
                                local_id,
                                drive_item['description'],
                                drive_item.get('thumbnailLink'),
                                drive_item.get('webContentLink'),
                                commit=False,
                            )
                            total_fusions += 1
                        except Exception as e:
                            logging.error(
                                f"❌ Erro ao fusionar metadados (ID local: {local_id}) a partir do Drive {file_id}: {e}")
                    matched_to_delete.append(file_id)

            processed += len(rows)
            indexer.conn.commit()
            if total_drive:
                pct = min(95, 80 + int((processed / total_drive) * 15))
                self.progress_update.emit(
                    pct, f"Fusão em andamento... {processed}/{total_drive}")

            offset += batch_size

        if matched_to_delete:
            self.delete_in_batches(cursor, 'files', matched_to_delete)
            self.delete_in_batches(cursor, 'search_index', matched_to_delete)
            indexer.conn.commit()

        return total_fusions

    def delete_in_batches(self, cursor, table, id_list, batch_size=500):
        for i in range(0, len(id_list), batch_size):
            batch = id_list[i:i+batch_size]
            placeholders = ','.join('?' for _ in batch)
            sql = f"DELETE FROM {table} WHERE file_id IN ({placeholders})"
            cursor.execute(sql, batch)
