#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database import FileIndexer


def rebuild_and_test():
    print("=== RECONSTRUINDO E TESTANDO ===")

    indexer = FileIndexer()

    # Reconstruir o índice
    indexer.rebuild_search_index_with_normalization()

    # Verificar imediatamente após reconstrução
    indexer.cursor.execute('SELECT COUNT(*) FROM search_index')
    count = indexer.cursor.fetchone()[0]
    print(f"\n📊 Registros após reconstrução: {count}")

    if count > 0:
        print("✅ Índice reconstruído com sucesso!")

        # Testar busca imediatamente
        print("\n=== TESTANDO BUSCA IMEDIATA ===")

        # Busca por 'doc'
        indexer.cursor.execute(
            'SELECT name FROM search_index WHERE search_index MATCH ? LIMIT 3', ('"doc"',))
        results = indexer.cursor.fetchall()
        print(f'Busca por "doc": {len(results)} resultados')
        for r in results:
            print(f'  - {r[0]}')

        # Busca por 'test'
        indexer.cursor.execute(
            'SELECT name FROM search_index WHERE search_index MATCH ? LIMIT 3', ('"test"',))
        results = indexer.cursor.fetchall()
        print(f'Busca por "test": {len(results)} resultados')
        for r in results:
            print(f'  - {r[0]}')

        # Testar busca com acentos (se encontrarmos arquivos com acentos)
        indexer.cursor.execute(
            'SELECT name, normalized_name FROM search_index WHERE name LIKE ? LIMIT 3', ('%ã%',))
        accented_files = indexer.cursor.fetchall()
        print(f'\nArquivos com acentos encontrados: {len(accented_files)}')
        for name, norm in accented_files:
            print(f'  Original: "{name}" -> Normalizado: "{norm}"')

    else:
        print("❌ Falha na reconstrução do índice")

    # Fechar conexão
    indexer.close()


if __name__ == "__main__":
    rebuild_and_test()
