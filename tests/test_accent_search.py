#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database import FileIndexer, normalize_text


def test_accent_search():
    indexer = FileIndexer()

    print('=== TESTE DE BUSCA COM ACENTOS ===')

    # Casos de teste
    test_cases = [
        ('açúcar', 'acucar'),
        ('ação', 'acao'),
        ('coração', 'coracao'),
        ('São Paulo', 'sao paulo'),
        ('música', 'musica'),
        ('Documentação', 'documentacao')
    ]

    for original, expected in test_cases:
        print(f'\n🔍 Testando: "{original}"')

        # Busca com acentos
        results_with_accents = indexer.load_files_paged(
            source=None, page=0, page_size=3, search_term=original,
            sort_by='name_asc', filter_type='all'
        )

        # Busca sem acentos
        results_without_accents = indexer.load_files_paged(
            source=None, page=0, page_size=3, search_term=expected,
            sort_by='name_asc', filter_type='all'
        )

        print(
            f'  Com acentos ("{original}"): {len(results_with_accents)} resultados')
        print(
            f'  Sem acentos ("{expected}"): {len(results_without_accents)} resultados')

        # Mostrar primeiros resultados se houver
        if results_with_accents:
            print(
                f'    Exemplo com acentos: {results_with_accents[0].get("name", "N/A")}')
        if results_without_accents:
            print(
                f'    Exemplo sem acentos: {results_without_accents[0].get("name", "N/A")}')

        # Verificar se retornam os mesmos resultados
        same_count = len(results_with_accents) == len(results_without_accents)
        status = '✅' if same_count else '⚠️'
        print(
            f'  Status: {status} {"Busca bidirecional funcionando" if same_count else "Resultados diferentes"}')

    indexer.close()
    print('\n=== TESTE CONCLUÍDO ===')


if __name__ == "__main__":
    test_accent_search()
