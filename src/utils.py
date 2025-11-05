# utils.py - Utilidades gerais do Vox Imago
#
# Responsável por:
# - Carregar e salvar configurações do sistema
# - Formatar tamanhos de arquivos para exibição
# - Buscar correspondências entre arquivos locais e do Drive
# - Outras funções auxiliares genéricas usadas em todo o projeto

import os
import json
from .database import normalize_text

SETTINGS_FILE = 'config/settings.json'


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)


def format_size(size_in_bytes):
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024**2:
        return f"{size_in_bytes / 1024:.2f} KB"
    elif size_in_bytes < 1024**3:
        return f"{size_in_bytes / 1024**2:.2f} MB"
    else:
        return f"{size_in_bytes / 1024**3:.2f} GB"


def find_local_matches(drive_file, local_files_cursor):

    matches = []
    drive_name = drive_file.get('name', '')
    drive_size = drive_file.get('size', 0)

    print(f"🔍 Procurando matches para: '{drive_name}' (tamanho: {drive_size})")

    local_files_cursor.execute(
        "SELECT file_id FROM files WHERE source='local' AND LOWER(name)=LOWER(?) AND size=?",
        (drive_name, drive_size)
    )
    exact_matches = local_files_cursor.fetchall()
    for match in exact_matches:
        matches.append(match[0])
        print(f"✅ Match EXATO encontrado: ID {match[0]}")

    if len(matches) == 0:
        drive_name_normalized = normalize_text(drive_name)
        print(
            f"🔍 Tentando busca normalizada: '{drive_name}' → '{drive_name_normalized}'")

        local_files_cursor.execute(
            "SELECT file_id, name FROM files WHERE source='local' AND size=?",
            (drive_size,)
        )
        candidates = local_files_cursor.fetchall()

        for file_id, local_name in candidates:
            local_name_normalized = normalize_text(local_name)
            if local_name_normalized.lower() == drive_name_normalized.lower():
                matches.append(file_id)
                print(
                    f"✅ Match NORMALIZADO encontrado: '{local_name}' → '{local_name_normalized}' (ID: {file_id})")

    return matches
