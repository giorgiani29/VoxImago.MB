"""
Script de teste de preservação - Valida que descrições locais são mantidas durante a fusão
Testa: preservação de metadados locais quando há conflito com dados do Drive
"""

from database.search import SearchEngine
from database.database import FileIndexer
import os
import sys
import sqlite3

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(repo_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


DB_PATH = 'data/test_preserve_desc.db'

# Clean DB
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

indexer = FileIndexer(DB_PATH)

# Step 1: insert local file with empty description
local_item = {
    'id': 'local_abc',
    'name': 'sample.pdf',
    'path': '/tmp/sample.pdf',
    'mimeType': 'application/pdf',
    'source': 'local',
    'description': '',
    'size': 1234,
    'modifiedTime': 111,
    'createdTime': 111,
}
indexer.save_files_in_batch([local_item], source='local')

# Step 2: simulate drive fusion that sets description
indexer.cursor.execute(
    "UPDATE files SET description = ? WHERE file_id = ?",
    ("Drive description here", local_item['id'])
)
indexer.cursor.execute(
    "UPDATE search_index SET description = ?, normalized_description = ? WHERE file_id = ?",
    ("Drive description here", SearchEngine(None).normalize_text(
        "Drive description here"), local_item['id'])
)
indexer.conn.commit()

# Verify desc is set
indexer.cursor.execute(
    "SELECT description FROM files WHERE file_id = ?", (local_item['id'],))
print('After fusion:', indexer.cursor.fetchone()[0])

# Step 3: run another local save with empty description again
indexer.save_files_in_batch([local_item], source='local')

# Verify desc was preserved
indexer.cursor.execute(
    "SELECT description FROM files WHERE file_id = ?", (local_item['id'],))
print('After rescan:', indexer.cursor.fetchone()[0])

# Also verify search_index normalized_description preserved
indexer.cursor.execute(
    "SELECT description, normalized_description FROM search_index WHERE file_id = ?", (local_item['id'],))
print('Search index:', indexer.cursor.fetchone())

indexer.close()
