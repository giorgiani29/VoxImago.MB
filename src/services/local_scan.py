import sys
import time
import os
import logging
from datetime import datetime, timezone
from PyQt6.QtCore import QObject, pyqtSignal
from src.database.database import FileIndexer


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='app.log',
    filemode='a'
)


class LocalScan(QObject):

    update_status_signal = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    total_files_found = pyqtSignal(int)
    finished = pyqtSignal()

    def terminate(self):
        logging.info("🚫 Cancelamento solicitado - parando escaneamento local")
        self.is_running = False
        self.update_status_signal.emit("Cancelando escaneamento...")

    def _count_total_files(self):
        total = 0
        self.update_status_signal.emit("Contando arquivos...")

        for scan_path in self.scan_path:
            if not os.path.exists(scan_path) or not self.is_running:
                continue

            for root, dirs, files in os.walk(scan_path):
                if not self.is_running:
                    break
                total += len(dirs)
                total += len([f for f in files if f.lower() != 'desktop.ini'])

                if total % 1000 == 0:
                    self.update_status_signal.emit(
                        f"Contados {total:,} itens...")

        return total

    def __init__(self, db_name, scan_path):
        super().__init__()
        self.db_name = db_name
        if isinstance(scan_path, str):
            self.scan_path = [scan_path]
        else:
            self.scan_path = scan_path
        self.is_running = True
        self.total_processed = 0
        self.indexer = None

    def run(self):
        logging.info(f"🟢 Iniciando escaneamento local: {self.scan_path}")
        start_time = time.time()

        total_items = self._count_total_files()
        if not self.is_running:
            return

        self.total_files_found.emit(total_items)
        logging.info(f"📊 Total de itens encontrados: {total_items:,}")

        self.update_status_signal.emit(
            f"Processando {total_items:,} arquivos...")

        self.indexer = FileIndexer(self.db_name)
        items_batch = []
        batch_size = 200

        total_processed = 0
        for scan_path in self.scan_path:
            logging.info(f"🔍 Escaneando caminho: {scan_path}")
            if not os.path.exists(scan_path):
                logging.error(f"❌ Caminho não existe: {scan_path}")
                continue
            if not self.is_running:
                break
            for root, dirs, files in os.walk(scan_path):
                if not self.is_running:
                    break
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
                    except (FileNotFoundError, PermissionError) as e:
                        logging.error(f"Erro ao acessar pasta {dir_path}: {e}")
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
                        'webContentLink': None,
                    }
                    items_batch.append(dir_item)
                    total_processed += 1
                    if len(items_batch) >= batch_size:
                        self._flush_batch(items_batch)
                        self.progress_update.emit(total_processed)
                        self.update_status_signal.emit(
                            f"Processados {total_processed} itens...")
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
                                f"Aviso: Tempo de modificação negativo para {file_path}")
                            continue
                    except (OSError, FileNotFoundError) as e:
                        logging.error(
                            f"Erro ao acessar arquivo {file_path}: {e}")
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
                        'webContentLink': None,
                    }
                    items_batch.append(file_item)
                    total_processed += 1
                    if len(items_batch) >= batch_size:
                        self._flush_batch(items_batch)
                        self.progress_update.emit(total_processed)
                        self.update_status_signal.emit(
                            f"Processados {total_processed} itens...")
        if items_batch:
            self._flush_batch(items_batch)
            self.total_processed += len(items_batch)
            self.progress_update.emit(self.total_processed)
        try:
            self.indexer.ensure_conn()
            self.indexer.cursor.execute(
                "SELECT COUNT(*), MIN(name), MAX(name) FROM files WHERE source='local'")
            count, min_name, max_name = self.indexer.cursor.fetchone()
            logging.info(
                f"✅ Scan local concluído: {count} arquivos locais. Min: {min_name}, Max: {max_name}")
        except Exception as e:
            logging.error(f"Erro ao contar arquivos locais: {e}")
        end_time = time.time()
        duration = end_time - start_time
        logging.info(
            f"⏹️ Fim do escaneamento local. Tempo total: {duration:.2f} segundos. Total processado: {total_processed}")

        self.progress_update.emit(total_processed)
        self.update_status_signal.emit(
            f"Concluído: {total_processed} itens processados.")

        if self.indexer:
            try:
                self.indexer.close()
            except Exception:
                pass

        self.finished.emit()

    def _flush_batch(self, items_batch):
        if not items_batch:
            return
        for attempt in range(3):
            try:
                self.indexer.save_files_in_batch(items_batch, source='local')
                self.indexer.conn.commit()
                items_batch.clear()
                return
            except Exception as e:
                logging.warning(
                    f"Tentativa {attempt+1}/3 ao salvar lote falhou: {e}")
                time.sleep(1)
        raise RuntimeError(
            "Falha ao persistir lote no banco de dados após 3 tentativas")


    def stop(self):
        self.is_running = False


def extrair_ano_banco_imagens(path):
    partes = os.path.normpath(path).split(os.sep)
    try:
        idx = partes.index('Banco de Imagens')
        ano = int(partes[idx + 1])
        return ano
    except (ValueError, IndexError):
        return None
