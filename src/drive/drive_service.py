"""
Módulo drive_service

Este módulo implementa a integração com a API do Google Drive no VoxImago.MB.
Fornece funções e classes para autenticação, upload, download, sincronização,
listagem e manipulação de arquivos e pastas no Google Drive.
"""

import logging
import time
from datetime import datetime


class DriveService:

    def __init__(self, service):
        self.service = service

    def get_shared_drives(self):
        try:
            drives_response = self.service.drives().list().execute()
            shared_drives = drives_response.get('drives', [])
            logging.info(f"🏢 Encontrados {len(shared_drives)} Shared Drives")
            return shared_drives
        except Exception as e:
            logging.error(f"❌ Erro ao buscar Shared Drives: {e}")
            return []

    def get_folders_in_drive(self, drive_id=None, parent_folder='root'):
        folders = []
        page_token = None

        try:
            while True:
                if drive_id and drive_id != 'root':
                    query = f"'{parent_folder}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                    response = self.service.files().list(
                        q=query,
                        fields="nextPageToken, files(id, name, parents)",
                        pageSize=50,
                        pageToken=page_token,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        corpora='drive',
                        driveId=drive_id
                    ).execute()
                else:
                    query = "mimeType='application/vnd.google-apps.folder' and trashed=false and 'root' in parents"
                    response = self.service.files().list(
                        q=query,
                        fields="nextPageToken, files(id, name, parents)",
                        pageSize=100,
                        pageToken=page_token
                    ).execute()

                page_folders = response.get('files', [])
                folders.extend(page_folders)

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            logging.info(
                f"📁 Encontradas {len(folders)} pastas em drive {drive_id or 'pessoal'}")
            return folders

        except Exception as e:
            logging.error(f"❌ Erro ao buscar pastas do drive {drive_id}: {e}")
            return []

    def get_all_subfolders_recursive(self, folder_id, shared_drive_id=None):
        all_folders = [folder_id]
        folders_to_check = [folder_id]

        logging.info(f"🔍 Coletando subpastas recursivamente de {folder_id}")

        while folders_to_check:
            current_folder = folders_to_check.pop(0)

            try:
                query = f"'{current_folder}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

                if shared_drive_id:
                    response = self.service.files().list(
                        q=query,
                        fields="files(id, name)",
                        pageSize=1000,
                        corpora='drive',
                        driveId=shared_drive_id,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True
                    ).execute()
                else:
                    response = self.service.files().list(
                        q=query,
                        fields="files(id, name)",
                        pageSize=1000,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True
                    ).execute()

                subfolders = response.get('files', [])
                for subfolder in subfolders:
                    subfolder_id = subfolder['id']
                    if subfolder_id not in all_folders:
                        all_folders.append(subfolder_id)
                        folders_to_check.append(subfolder_id)
                        logging.info(
                            f"📁 Encontrada subpasta: {subfolder.get('name', 'sem nome')} ({subfolder_id})")

            except Exception as e:
                logging.error(
                    f"❌ Erro buscando subpastas de {current_folder}: {e}")
                continue

        logging.info(
            f"✅ Total de {len(all_folders)} pastas encontradas (incluindo subpastas)")
        return all_folders

    def count_files_in_folders(self, folder_ids, shared_drive_id=None):
        total_files = 0
        logging.info(f"🔢 Contando arquivos em {len(folder_ids)} pastas...")

        for folder_id in folder_ids:
            try:
                query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"

                if shared_drive_id:
                    response = self.service.files().list(
                        q=query,
                        fields="files(id)",
                        pageSize=1000,
                        corpora='drive',
                        driveId=shared_drive_id,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True
                    ).execute()
                else:
                    response = self.service.files().list(
                        q=query,
                        fields="files(id)",
                        pageSize=1000,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True
                    ).execute()

                files_count = len(response.get('files', []))
                total_files += files_count

                if files_count > 0:
                    logging.info(
                        f"📁 Pasta {folder_id}: {files_count} arquivos")

            except Exception as e:
                logging.error(f"❌ Erro contando arquivos em {folder_id}: {e}")
                continue

        logging.info(f"📊 Total de arquivos: {total_files}")
        return total_files

    def list_files_paginated(self, base_q, is_shared_drive_sync, shared_drive_id, page_token=None, page_size=1000, recursive_folders=None, fields_override=None):
        try:
            fields = fields_override or "nextPageToken, files(id, name, mimeType, description, parents, modifiedTime, createdTime, size, webViewLink, thumbnailLink)"

            if is_shared_drive_sync:
                response = self.service.files().list(
                    q=base_q,
                    fields=fields,
                    pageSize=page_size,
                    pageToken=page_token,
                    corpora='drive',
                    driveId=shared_drive_id,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True
                ).execute()
            elif recursive_folders:
                response = self.service.files().list(
                    q=base_q,
                    fields=fields,
                    pageSize=page_size,
                    pageToken=page_token,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True
                ).execute()
            else:
                response = self.service.files().list(
                    q=base_q,
                    fields=fields,
                    pageSize=page_size,
                    pageToken=page_token,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True
                ).execute()

            return response

        except Exception as e:
            logging.error(f"❌ Erro na API do Google Drive: {e}")
            raise e

    def test_api_connection(self):
        try:
            test_response = self.service.files().list(
                q="trashed = false", pageSize=1).execute()
            test_files = test_response.get('files', [])
            logging.info(
                f"✅ Teste API: {len(test_files)} arquivo(s) encontrado(s)")
            if test_files:
                logging.info(
                    f"   Exemplo: {test_files[0].get('name', 'sem nome')}")
            return True
        except Exception as e:
            logging.error(f"❌ Erro no teste da API: {e}")
            return False
