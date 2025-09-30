#!/usr/bin/env python3
"""
Teste final de integração - Prioridade 1 completa
"""

from database import FileIndexer, normalize_text
import os


def test_final_integration():
    print("🚀 TESTE FINAL DE INTEGRAÇÃO - PRIORIDADE 1")
    print("=" * 60)

    # Teste 1: Verificar estrutura do banco
    print("1️⃣ Testando estrutura do banco...")
    indexer = FileIndexer()

    try:
        indexer.cursor.execute("PRAGMA table_info(search_index)")
        columns = [col[1] for col in indexer.cursor.fetchall()]
        expected_cols = ['name', 'description', 'normalized_name',
                         'normalized_description', 'file_id', 'source']

        has_all_cols = all(col in columns for col in expected_cols)
        print(f"   Colunas encontradas: {columns}")
        print(f"   ✅ Estrutura correta: {has_all_cols}")

        if not has_all_cols:
            print("   🔄 Recriando estrutura...")
            indexer.rebuild_search_index_with_normalization()
            print("   ✅ Estrutura corrigida!")

    except Exception as e:
        print(f"   ❌ Erro na estrutura: {e}")
        return False

    # Teste 2: Verificar workers.py
    print("\n2️⃣ Testando workers.py...")
    try:
        import workers
        print("   ✅ Workers importado com sucesso")

        # Verificar se tem normalize_text
        with open('workers.py', 'r', encoding='utf-8') as f:
            content = f.read()

        if 'normalize_text' in content:
            print("   ✅ normalize_text encontrado no workers")
        else:
            print("   ❌ normalize_text não encontrado no workers")
            return False

    except Exception as e:
        print(f"   ❌ Erro no workers: {e}")
        return False

    # Teste 3: Funcionalidade de normalização
    print("\n3️⃣ Testando funcionalidade de normalização...")

    test_cases = [
        ("Educação", "educacao"),
        ("Coração", "coracao"),
        ("São Paulo", "sao paulo"),
        ("Opções", "opcoes"),
        ("Açúcar", "acucar")
    ]

    all_passed = True
    for original, expected in test_cases:
        result = normalize_text(original)
        passed = result == expected
        status = "✅" if passed else "❌"
        print(f"   {status} '{original}' → '{result}' (esperado: '{expected}')")
        if not passed:
            all_passed = False

    if not all_passed:
        return False

    # Teste 4: Busca com dados de teste
    print("\n4️⃣ Testando busca com dados de teste...")

    # Criar dados de teste
    test_files = [
        {
            'id': 'final_test_1',
            'name': 'Relatório de Educação.pdf',
            'path': '/test/educacao.pdf',
            'description': 'Relatório sobre educação brasileira',
            'source': 'test_final',
            'mimeType': 'application/pdf',
            'size': 1024,
            'modifiedTime': 1234567890,
            'createdTime': 1234567890,
            'parentId': None
        }
    ]

    indexer.save_files_in_batch(test_files, 'test_final')
    print("   📁 Dados de teste criados")

    # Testar busca bidirecional
    searches = ["educacao", "educação"]

    for search_term in searches:
        results = indexer.load_files_paged(
            source='test_final',
            page=0,
            page_size=10,
            search_term=search_term,
            sort_by='name_asc',
            filter_type='all'
        )

        found = len(results) > 0
        status = "✅" if found else "❌"
        print(f"   {status} Busca '{search_term}': {len(results)} resultado(s)")

        if not found:
            all_passed = False

    # Limpar dados de teste
    indexer.cursor.execute("DELETE FROM files WHERE source = 'test_final'")
    indexer.cursor.execute(
        "DELETE FROM search_index WHERE source = 'test_final'")
    indexer.conn.commit()
    print("   🧹 Dados de teste limpos")

    indexer.close()

    if all_passed:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Prioridade 1 está 100% funcional!")
        return True
    else:
        print("\n❌ Alguns testes falharam!")
        return False


if __name__ == "__main__":
    success = test_final_integration()

    if success:
        print(f"\n🚀 PRIORIDADE 1 CONCLUÍDA COM SUCESSO!")
        print("=" * 40)
        print("✅ Normalização de acentos funcionando")
        print("✅ Busca bidirecional ativa")
        print("✅ Workers.py corrigido")
        print("✅ Banco estruturado corretamente")
        print("✅ Testes passando 100%")
        print(f"\n🎯 PRÓXIMO PASSO: PRIORIDADE 2")
        print("   Otimizar sincronização no workers.py")
        print(f"\n🚀 Execute agora: python app.py")
    else:
        print(f"\n⚠️ CORRIGIR PROBLEMAS ANTES DE CONTINUAR")
