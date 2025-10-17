#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark de performance para operações de matching e busca
"""

from src.database import FileIndexer
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def benchmark_matching():
    """Executa benchmarks de performance para operações de banco"""
    try:
        indexer = FileIndexer()
    except Exception as e:
        print(f"❌ Erro ao inicializar FileIndexer: {e}")
        return False

    source = 'local'
    filter_type = 'image'
    advanced_filters = {'extension': '.jpg'}
    folder_id = None
    search_term = None

    try:
        print('📊 Benchmark: count_files')
        start = time.time()
        count = indexer.count_files(
            source, search_term, filter_type, folder_id, advanced_filters)
        elapsed = time.time() - start
        print(f'✅ Count: {count}, Tempo: {elapsed:.4f}s')

    except Exception as e:
        print(f"❌ Erro no benchmark count_files: {e}")
        return False

    try:
        print('📊 Benchmark: load_files_paged')
        start = time.time()
        files = indexer.load_files_paged(
            source, 0, 100, search_term, 'name_asc', filter_type, folder_id, advanced_filters)
        elapsed = time.time() - start
        print(f'✅ Arquivos: {len(files)}, Tempo: {elapsed:.4f}s')
        return True

    except Exception as e:
        print(f"❌ Erro no benchmark load_files_paged: {e}")
        return False
    finally:
        try:
            indexer.close()
        except Exception as e:
            print(f"⚠️ Erro ao fechar indexer: {e}")


if __name__ == '__main__':
    try:
        success = benchmark_matching()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro fatal no benchmark: {e}")
        sys.exit(1)
