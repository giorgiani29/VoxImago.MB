"""
Teste de cache do banco de dados
"""

import time
from src.database import FileIndexer


def test_cache():
    indexer = FileIndexer()
    source = 'local'
    search_term = None
    filter_type = 'image'
    folder_id = None
    advanced_filters = {'extension': '.jpg'}

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
    print('Teste de cache de count_files OK!')

    print('Testando cache de load_files_paged:')
    start = time.time()
    files1 = indexer.load_files_paged(
        source, 0, 10, search_term, 'name_asc', filter_type, folder_id, advanced_filters)
    elapsed1 = time.time() - start
    print(f'Arquivos: {len(files1)}, Tempo: {elapsed1:.4f}s')

    start = time.time()
    files2 = indexer.load_files_paged(
        source, 0, 10, search_term, 'name_asc', filter_type, folder_id, advanced_filters)
    elapsed2 = time.time() - start
    print(f'Arquivos: {len(files2)}, Tempo: {elapsed2:.4f}s')

    assert files1 == files2, 'Os resultados devem ser iguais.'
    assert elapsed2 < elapsed1, 'A segunda chamada deve ser mais rápida (cache).'
    print('Teste de cache de load_files_paged OK!')


if __name__ == '__main__':
    test_cache()
