"""
Script para encontrar duplicatas no Google Drive - Localiza arquivos duplicados por hash MD5
Salva lista de IDs duplicados em 'drive_duplicados_ids.txt' para posterior limpeza
"""

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
from collections import defaultdict

TOKEN_FILE = 'config/token.json'
CREDENTIALS_FILE = 'config/credentials.json'

SHARED_DRIVE_ID = '0AOB-ISqqs76_Uk9PVA'


print("[DEBUG] Iniciando autenticação...")
creds = Credentials.from_authorized_user_file(TOKEN_FILE)
service = build('drive', 'v3', credentials=creds)

print(f"[DEBUG] Buscando arquivos no Shared Drive: {SHARED_DRIVE_ID}")
results = []
page_token = None
total_files = 0
while True:
    response = service.files().list(
        corpora='drive',
        driveId=SHARED_DRIVE_ID,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields='nextPageToken, files(id, name, md5Checksum)',
        pageSize=1000,
        pageToken=page_token
    ).execute()
    batch = response.get('files', [])
    results.extend(batch)
    total_files += len(batch)
    print(f"[DEBUG] Lidos {total_files} arquivos até agora...")
    page_token = response.get('nextPageToken', None)
    if not page_token:
        break

print(f"[DEBUG] Total de arquivos processados: {total_files}")

hash_map = defaultdict(list)
for file in results:
    md5 = file.get('md5Checksum')
    if md5:
        hash_map[md5].append(file['id'])

print(f"[DEBUG] Total de hashes únicos: {len(hash_map)}")

duplicados = [ids for ids in hash_map.values() if len(ids) > 1]
print(f"[DEBUG] Total de grupos duplicados encontrados: {len(duplicados)}")

for i, grupo in enumerate(duplicados[:5]):
    print(f"[DEBUG] Grupo duplicado {i+1}: {grupo}")

with open('drive_duplicados_ids.txt', 'w') as f:
    for grupo in duplicados:
        for file_id in grupo:
            f.write(file_id + '\n')

print(
    f"[DEBUG] Encontrados {sum(len(g) for g in duplicados)} arquivos duplicados pelo hash. IDs salvos em drive_duplicados_ids.txt.")
