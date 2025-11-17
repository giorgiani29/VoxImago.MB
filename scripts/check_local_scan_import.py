"""
Script de teste de importação - Verifica se o módulo LocalScan pode ser importado corretamente
Testa: import paths e inicialização do LocalScan
"""

from src.services.local_scan import LocalScan
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


if __name__ == '__main__':
    ls_inc = LocalScan('data/file_index.db', '.', False)
    print('inc.force_sync:', ls_inc.force_sync)
    print('inc.last_sync:', ls_inc.get_last_sync_time())
    ls_forced = LocalScan('data/file_index.db', '.', True)
    print('forced.force_sync:', ls_forced.force_sync)
    print('forced.last_sync:', ls_forced.get_last_sync_time())
