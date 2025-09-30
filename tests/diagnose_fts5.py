#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3


def diagnose_fts5():
    conn = sqlite3.connect('file_index.db')
    cursor = conn.cursor()

    print('=== DIAGNÓSTICO FTS5 ===')

    # Verificar se há dados no search_index
    cursor.execute('SELECT COUNT(*) FROM search_index')
    count = cursor.fetchone()[0]
    print(f'Total registros search_index: {count}')

    # Verificar uma amostra dos dados
    cursor.execute('SELECT name, normalized_name FROM search_index LIMIT 5')
    sample = cursor.fetchall()
    print('Amostra dos dados:')
    for row in sample:
        print(f'  Nome: "{row[0]}" -> Normalizado: "{row[1]}"')

    # Testar consulta FTS direta
    print('\nTeste FTS5 direto:')
    try:
        cursor.execute(
            'SELECT name FROM search_index WHERE search_index MATCH ? LIMIT 3', ('doc',))
        results = cursor.fetchall()
        print(f'FTS "doc" direto: {len(results)} resultados')
        for r in results:
            print(f'  - {r[0]}')
    except Exception as e:
        print(f'Erro FTS direto: {e}')

    # Testar com trigram
    print('\nTeste com trigram:')
    try:
        cursor.execute(
            'SELECT name FROM search_index WHERE search_index MATCH ? LIMIT 3', ('"doc*"',))
        results = cursor.fetchall()
        print(f'FTS "doc*" com trigram: {len(results)} resultados')
        for r in results:
            print(f'  - {r[0]}')
    except Exception as e:
        print(f'Erro FTS trigram: {e}')

    # Testar busca por DDS (sabemos que existe)
    try:
        cursor.execute(
            'SELECT name FROM search_index WHERE search_index MATCH ? LIMIT 3', ('"dds"',))
        results = cursor.fetchall()
        print(f'FTS "dds": {len(results)} resultados')
        for r in results:
            print(f'  - {r[0]}')
    except Exception as e:
        print(f'Erro FTS dds: {e}')

    conn.close()


if __name__ == "__main__":
    diagnose_fts5()
