import time
from src.database import FileIndexer


def benchmark_matching():
    indexer = FileIndexer()
    source = 'local'
    filter_type = 'image'
    advanced_filters = {'extension': '.jpg'}
    folder_id = None
    search_term = None

    print('Benchmark: count_files')
    start = time.time()
    count = indexer.count_files(
        source, search_term, filter_type, folder_id, advanced_filters)
    elapsed = time.time() - start
    print(f'Count: {count}, Tempo: {elapsed:.4f}s')

    print('Benchmark: load_files_paged')
    start = time.time()
    files = indexer.load_files_paged(
        source, 0, 100, search_term, 'name_asc', filter_type, folder_id, advanced_filters)
    elapsed = time.time() - start
    print(f'Arquivos: {len(files)}, Tempo: {elapsed:.4f}s')


if __name__ == '__main__':
    benchmark_matching()
