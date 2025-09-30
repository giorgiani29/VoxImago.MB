#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from database import FileIndexer


def check_real_content():
    conn = sqlite3.connect('file_index.db')
    cursor = conn.cursor()

    print('=== VERIFICANDO CONTEÚDO REAL ===')

    # Buscar arquivos com 'doc'
    cursor.execute(
        'SELECT name FROM files WHERE name LIKE ? LIMIT 5', ('%doc%',))
    results = cursor.fetchall()
    print('Arquivos com "doc":')
    for r in results:
        print(f'  - {r[0]}')

    # Buscar arquivos com 'plan'
    cursor.execute(
        'SELECT name FROM files WHERE name LIKE ? LIMIT 5', ('%plan%',))
    results = cursor.fetchall()
    print('\nArquivos com "plan":')
    for r in results:
        print(f'  - {r[0]}')

    # Buscar arquivos com 'jpg'
    cursor.execute(
        'SELECT name FROM files WHERE name LIKE ? LIMIT 5', ('%jpg%',))
    results = cursor.fetchall()
    print('\nArquivos com "jpg":')
    for r in results:
        print(f'  - {r[0]}')

    # Testar busca FTS com termos existentes
    print('\n=== TESTANDO BUSCA FTS ===')
    indexer = FileIndexer()

    test_terms = ['doc', 'plan', 'jpg', 'test']

    for term in test_terms:
        results = indexer.load_files_paged(
            source=None, page=0, page_size=3, search_term=term,
            sort_by='name_asc', filter_type='all'
        )
        print(f'FTS "{term}": {len(results)} resultados')
        if results:
            print(f'  Primeiro: {results[0].get("name", "N/A")}')

    indexer.close()
    conn.close()


if __name__ == "__main__":
    check_real_content()
