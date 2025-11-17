"""
Script de teste de cache - Valida performance e funcionamento do sistema de cache do banco
Testa: cache de count_files e load_files_paged para otimização de consultas
"""

from database.database import FileIndexer
from database.search import SearchEngine
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_cache():
    try:
        indexer = FileIndexer()
        search_engine = SearchEngine(indexer)
    except Exception as e:
        print(f"❌ Erro ao inicializar FileIndexer: {e}")
        return False

    source = 'local'
    search_term = None
    filter_type = 'image'
    folder_id = None
    advanced_filters = {'extension': '.jpg'}

    try:
        print('Primeira chamada (sem cache):')
        start = time.time()
        count1 = indexer.count_files(
            source, search_term, filter_type, folder_id, advanced_filters)
        elapsed1 = time.time() - start
        print(f'Count: {count1}, Tempo: {elapsed1:.4f}s')

        print('Segunda chamada (com cache):')
        start = time.time()
        count2 = indexer.count_files(
            source, search_term, filter_type, folder_id, advanced_filters)
        elapsed2 = time.time() - start
        print(f'Count: {count2}, Tempo: {elapsed2:.4f}s')

        assert count1 == count2, 'Os resultados devem ser iguais.'
        assert elapsed2 < elapsed1, 'A segunda chamada deve ser mais rápida (cache).'
        print('✅ Teste de cache de count_files OK!')

    except AssertionError as e:
        print(f"❌ Falha na asserção: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro no teste de count_files: {e}")
        return False

    try:
        print('Testando cache de load_files_paged:')
        start = time.time()
        files1 = search_engine.load_files_paged(
            source, 0, 10, search_term, 'name_asc', filter_type, folder_id, advanced_filters)
        elapsed1 = time.time() - start
        print(f'Arquivos: {len(files1)}, Tempo: {elapsed1:.4f}s')

        start = time.time()
        files2 = search_engine.load_files_paged(
            source, 0, 10, search_term, 'name_asc', filter_type, folder_id, advanced_filters)
        elapsed2 = time.time() - start
        print(f'Arquivos: {len(files2)}, Tempo: {elapsed2:.4f}s')

        assert files1 == files2, 'Os resultados devem ser iguais.'
        assert elapsed2 < elapsed1, 'A segunda chamada deve ser mais rápida (cache).'
        print('✅ Teste de cache de load_files_paged OK!')
        return True

    except AssertionError as e:
        print(f"❌ Falha na asserção: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro no teste de load_files_paged: {e}")
        return False
    finally:
        try:
            indexer.close()
        except Exception as e:
            print(f"⚠️ Erro ao fechar indexer: {e}")


if __name__ == "__main__":
    try:
        success = test_cache()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro fatal no teste: {e}")
        sys.exit(1)


if __name__ == '__main__':
    test_cache()
