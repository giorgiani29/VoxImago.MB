"""
Módulo match

Este módulo implementa algoritmos e funções para comparação e correspondência de arquivos
entre o sistema local e o Google Drive no VoxImago.MB. Fornece utilitários para identificar
arquivos duplicados, verificar similaridade, e auxiliar nos processos de sincronização e fusão.
"""

from src.database.search import SearchEngine
import os
import string
import unicodedata

DRIVE_SHORTCUT_EXTENSIONS = [
    '.gdoc', '.gsheet', '.gslides', '.gdraw', '.gform']


def normalize_aggressive(name):
    if not name:
        return ''

    name_wo_ext, ext = os.path.splitext(name)
    base_name = name_wo_ext

    name_norm = unicodedata.normalize('NFD', base_name)
    name_no_accents = ''.join(
        c for c in name_norm if unicodedata.category(c) != 'Mn')
    table = str.maketrans('', '', string.punctuation + string.whitespace)
    return name_no_accents.translate(table).lower()


def normalize_name_only(name):
    if not name:
        return ''

    name_base = os.path.splitext(name)[0]

    name_norm = unicodedata.normalize('NFD', name_base)
    name_clean = ''.join(
        c for c in name_norm if unicodedata.category(c) != 'Mn')
    table = str.maketrans('', '', string.punctuation + string.whitespace)
    return name_clean.translate(table).lower()


def find_local_matches(drive_file, local_files_cursor):
    import logging
    import time
    from difflib import SequenceMatcher

    matches = []
    drive_name = drive_file.get('name', '')
    drive_size = drive_file.get('size', 0)
    drive_id = drive_file.get('id', '')

    if not drive_name:
        logging.warning(f"⚠️  Nome vazio para arquivo Drive ID: {drive_id}")
        return matches

    start_time = time.perf_counter()

    logging.info(
        f"🔍 [OTIMIZADO] Matching para: '{drive_name}' (ID: {drive_id[:8]}..., {drive_size} bytes)")

    search_engine = SearchEngine(None)
    drive_name_normalized = search_engine.normalize_text(drive_name)
    drive_name_aggressive = normalize_aggressive(drive_name)

    phase_start = time.perf_counter()
    local_files_cursor.execute(
        "SELECT file_id, name, size FROM files WHERE source='local' AND LOWER(name)=LOWER(?) LIMIT 1",
        (drive_name,)
    )
    exact_match = local_files_cursor.fetchone()
    phase_time = (time.perf_counter() - phase_start) * 1000

    if exact_match:
        total_time = (time.perf_counter() - start_time) * 1000
        matches.append(exact_match[0])
        logging.info(
            f"✅ [FASE 1] Match EXATO: '{exact_match[1]}' (ID: {exact_match[0][:8]}...) | {phase_time:.2f}ms | Total: {total_time:.2f}ms")
        return matches
    else:
        logging.debug(
            f"🔍 [FASE 1] Sem match exato para '{drive_name}' | {phase_time:.2f}ms")

    if drive_name_normalized:
        phase_start = time.perf_counter()
        local_files_cursor.execute(
            "SELECT file_id, name, size FROM files WHERE source='local' AND name_normalized=? LIMIT 1",
            (drive_name_normalized,)
        )
        normalized_match = local_files_cursor.fetchone()
        phase_time = (time.perf_counter() - phase_start) * 1000

        if normalized_match:
            total_time = (time.perf_counter() - start_time) * 1000
            matches.append(normalized_match[0])
            logging.info(
                f"✅ [FASE 2] Match NORMALIZADO: '{normalized_match[1]}' (ID: {normalized_match[0][:8]}...) | '{drive_name}' → '{drive_name_normalized}' | {phase_time:.2f}ms | Total: {total_time:.2f}ms")
            return matches
        else:
            logging.debug(
                f"🔍 [FASE 2] Sem match normalizado: '{drive_name}' → '{drive_name_normalized}' | {phase_time:.2f}ms")

    if drive_name_aggressive:
        phase_start = time.perf_counter()
        local_files_cursor.execute(
            "SELECT file_id, name, size FROM files WHERE source='local' AND name_aggressive=? LIMIT 1",
            (drive_name_aggressive,)
        )
        aggressive_match = local_files_cursor.fetchone()
        phase_time = (time.perf_counter() - phase_start) * 1000

        if aggressive_match:
            total_time = (time.perf_counter() - start_time) * 1000
            matches.append(aggressive_match[0])
            logging.info(
                f"✅ [FASE 3] Match AGRESSIVO: '{aggressive_match[1]}' (ID: {aggressive_match[0][:8]}...) | '{drive_name}' → '{drive_name_aggressive}' | {phase_time:.2f}ms | Total: {total_time:.2f}ms")
            return matches
        else:
            logging.debug(
                f"🔍 [FASE 3] Sem match agressivo: '{drive_name}' → '{drive_name_aggressive}' | {phase_time:.2f}ms")

    if not matches:
        drive_name_only = normalize_name_only(drive_name)
        if drive_name_only:
            phase_start = time.perf_counter()
            local_files_cursor.execute(
                "SELECT file_id, name, size FROM files WHERE source='local' AND name_aggressive LIKE ? LIMIT 1",
                (drive_name_only + '%',)
            )
            name_only_match = local_files_cursor.fetchone()
            phase_time = (time.perf_counter() - phase_start) * 1000

            if name_only_match:
                total_time = (time.perf_counter() - start_time) * 1000
                matches.append(name_only_match[0])
                logging.info(
                    f"✅ [FASE 4] Match NOME-ONLY: '{name_only_match[1]}' (ID: {name_only_match[0][:8]}...) | '{drive_name}' → '{drive_name_only}' | {phase_time:.2f}ms | Total: {total_time:.2f}ms")
                return matches
            else:
                logging.debug(
                    f"🔍 [FASE 4] Sem match nome-only: '{drive_name}' → '{drive_name_only}' | {phase_time:.2f}ms")

    if not matches:
        total_time = (time.perf_counter() - start_time) * 1000
        logging.warning(
            f"❌ [SEM MATCH] '{drive_name}' (ID: {drive_id[:8]}..., {drive_size} bytes) | Tempo total: {total_time:.2f}ms")

        if logging.getLogger().isEnabledFor(logging.DEBUG):
            local_files_cursor.execute(
                "SELECT name, size FROM files WHERE source='local' LIMIT 3"
            )
            close_candidates = local_files_cursor.fetchall()
            if close_candidates:
                exemplos = [f"'{n}' ({s} bytes)" for n, s in close_candidates]
                logging.debug(f"Exemplos locais: {', '.join(exemplos)}")

    return matches
