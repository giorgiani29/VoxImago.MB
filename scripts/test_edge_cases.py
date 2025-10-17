"""
Teste de casos extremos para busca FTS5
"""

import sqlite3

print('🧪 TESTE DE CASOS EXTREMOS')
print('=' * 50)

conn = sqlite3.connect('data/test_file_index.db')
cursor = conn.cursor()

print('\n1. CARACTERES ESPECIAIS:')
special_tests = [
    'josé',
    'são',
    'joão',
    'ção',
    'pará',
    'açúcar'
]

for term in special_tests:
    try:
        cursor.execute(
            'SELECT name FROM search_index WHERE search_index MATCH ?', (term,))
        results = cursor.fetchall()
        print(f'  {term}: {len(results)} resultados')
    except Exception as e:
        print(f'  {term}: ERRO - {e}')

print('\n2. OPERADORES COMPLEXOS:')
complex_tests = [
    '(jesus OR carol) AND (2020 OR 2021)',
    'jesus* NOT natal*',
    'pe AND gilson AND brasil',
    'haiti NEAR(5) 2021'
]

for query in complex_tests:
    try:
        cursor.execute(
            'SELECT name FROM search_index WHERE search_index MATCH ?', (query,))
        results = cursor.fetchall()
        print(f'  {query}: {len(results)} resultados')
    except Exception as e:
        print(f'  {query}: ERRO - {str(e)[:50]}')

print('\n3. EDGE CASES:')
edge_cases = [
    ('vazio', ''),
    ('espaço', ' '),
    ('inexistente', 'xxxnonexistentxxx'),
    ('números', '123456789'),
    ('letra única', 'a'),
    ('muito longo', 'a' * 50)
]

for desc, term in edge_cases:
    try:
        cursor.execute(
            'SELECT name FROM search_index WHERE search_index MATCH ?', (term,))
        results = cursor.fetchall()
        print(f'  {desc} ("{term[:10]}..."): {len(results)} resultados')
    except Exception as e:
        print(f'  {desc}: ERRO - {str(e)[:30]}')

conn.close()
print('\n✅ Teste de casos extremos concluído')
