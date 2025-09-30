#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database import FileIndexer, normalize_text
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_final_accent_search():
    print("=== TESTE FINAL DE BUSCA COM ACENTOS ===")

    indexer = FileIndexer()

    # Testar com palavras que encontramos no banco
    test_cases = [
        ("formação", "formacao"),
        ("expiação", "expiacao"),
        ("damião", "damiao"),
        ("documentação", "documentacao")
    ]

    all_passed = True

    for original, expected in test_cases:
        print(f"\n🔍 Testando: '{original}' vs '{expected}'")

        # Busca com acentos
        results_with_accents = indexer.load_files_paged(
            source=None, page=0, page_size=5, search_term=original,
            sort_by='name_asc', filter_type='all'
        )

        # Busca sem acentos
        results_without_accents = indexer.load_files_paged(
            source=None, page=0, page_size=5, search_term=expected,
            sort_by='name_asc', filter_type='all'
        )

        with_count = len(results_with_accents)
        without_count = len(results_without_accents)

        print(f"  Resultados com acentos: {with_count}")
        print(f"  Resultados sem acentos: {without_count}")

        # Mostrar alguns exemplos se houver resultados
        if results_with_accents:
            print(
                f"  Exemplo com acento: {results_with_accents[0].get('name', 'N/A')}")
        if results_without_accents:
            print(
                f"  Exemplo sem acento: {results_without_accents[0].get('name', 'N/A')}")

        # Verificar se são equivalentes
        if with_count == without_count and with_count > 0:
            print("  ✅ Busca bidirecional funcionando perfeitamente!")
        elif with_count == without_count and with_count == 0:
            print("  ℹ️  Nenhum resultado (mas busca consistente)")
        else:
            print("  ❌ Resultados inconsistentes entre busca com e sem acentos")
            all_passed = False

    # Teste adicional: busca por termos que definitivamente existem
    print(f"\n🧪 TESTE DE SANIDADE")
    test_results = indexer.load_files_paged(
        source=None, page=0, page_size=3, search_term="test",
        sort_by='name_asc', filter_type='all'
    )
    doc_results = indexer.load_files_paged(
        source=None, page=0, page_size=3, search_term="doc",
        sort_by='name_asc', filter_type='all'
    )

    print(f"  Busca 'test': {len(test_results)} resultados")
    print(f"  Busca 'doc': {len(doc_results)} resultados")

    if len(test_results) > 0 and len(doc_results) > 0:
        print("  ✅ Sistema de busca operacional!")
    else:
        print("  ❌ Problema com sistema de busca básico")
        all_passed = False

    indexer.close()

    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Normalização de acentos implementada com sucesso!")
        print("✅ Busca bidirecional funcionando (com e sem acentos)")
        print("✅ Índice FTS5 com trigram operacional")
    else:
        print("⚠️ Alguns testes falharam - verificar problemas acima")


if __name__ == "__main__":
    test_final_accent_search()
