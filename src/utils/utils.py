
# utils.py - Utilidades gerais do Vox Imago
#
# Responsável por:
# - Carregar e salvar configurações do sistema
# - Formatar tamanhos de arquivos para exibição
# - Buscar correspondências entre arquivos locais e do Drive
# - Outras funções auxiliares genéricas usadas em todo o projeto

import os
import json
from src.database.search import SearchEngine

SETTINGS_FILE = 'config/settings.json'


def resolve_shared_folder_path(possible_names, base_paths=None, drive_letters=None):
    if base_paths is None:
        base_paths = ["Drives compartilhados", "Shared drives"]
    if drive_letters is None:
        drive_letters = ["L:"]
    for drive in drive_letters:
        for base in base_paths:
            for name in possible_names:
                path = os.path.join(drive, base, name)
                if os.path.exists(path):
                    return path
    return None


def filter_existing_files(file_records, path_key='caminho'):

    return [f for f in file_records if f.get(path_key) and os.path.exists(f[path_key])]


def get_existing_files(file_records):
    return [f for f in file_records if os.path.exists(f['path'])]


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

    return matches


def extrair_ano_banco_imagens(path):
    partes = os.path.normpath(path).split(os.sep)
    try:
        idx = partes.index('Banco de Imagens')
        ano = int(partes[idx + 1])
        return ano
    except (ValueError, IndexError):
        return None
