"""
Teste de rollback de transações no banco de dados
"""

import os
import shutil
from src.database import FileIndexer


def setup_test_db():
    test_db = 'data/test_rollback.db'
    if os.path.exists(test_db):
        os.remove(test_db)
    return FileIndexer(test_db)


def test_normal_batch():
    db = setup_test_db()
    files = [
        {'id': '1', 'name': 'A.txt', 'path': '/tmp/A.txt',
            'mimeType': 'text/plain', 'source': 'local'},
        {'id': '2', 'name': 'B.txt', 'path': '/tmp/B.txt',
            'mimeType': 'text/plain', 'source': 'local'}
    ]
    db.save_files_in_batch(files, 'local')
    count = db.get_file_count('local')
    print(f"Normal batch: {count} arquivos salvos (esperado: 2)")
    db.close()


def test_rollback_batch():
    db = setup_test_db()
    files = [
        {'id': '3', 'name': 'C.txt', 'path': '/tmp/C.txt',
            'mimeType': 'text/plain', 'source': 'local'},
        {'id': '4', 'name': 'D.txt', 'path': '/tmp/D.txt',
            'mimeType': 'text/plain', 'source': 'local'}
    ]
    try:
        db.save_files_in_batch(files, 'local')
    except Exception as e:
        print(f"Erro capturado: {e}")
    count = db.get_file_count('local')
    print(f"Após rollback: {count} arquivos salvos (esperado: 0)")
    db.close()


if __name__ == "__main__":
    print("--- Teste de transação normal ---")
    test_normal_batch()
    print("--- Teste de rollback (simulação de erro) ---")
    test_rollback_batch()
