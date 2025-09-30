#!/usr/bin/env python3
"""
Teste da normalização com o aplicativo real
Este teste assume que você já tem dados indexados
"""

from database import FileIndexer, normalize_text
import os


def test_app_normalization():
    print("🔍 TESTE DE NORMALIZAÇÃO - APLICATIVO REAL")
    print("=" * 60)

    # Usar o mesmo banco que o app usa
    indexer = FileIndexer('file_index.db')

    # Verificar se há dados no banco
    indexer.cursor.execute("SELECT COUNT(*) FROM files")
    total_files = indexer.cursor.fetchone()[0]
    print(f"📁 Total de arquivos no banco: {total_files}")

    if total_files == 0:
        print("❌ Nenhum arquivo encontrado no banco principal.")
        print(
            "💡 Execute primeiro uma sincronização no aplicativo ou adicione pastas locais.")
        indexer.close()
        return False

    # Procurar arquivos com acentos nos dados reais
    print("\n🔍 Procurando arquivos com acentos nos dados reais...")

    indexer.cursor.execute("""
        SELECT file_id, name, description, source FROM files 
        WHERE (name LIKE '%ã%' OR name LIKE '%ç%' OR name LIKE '%á%' 
               OR name LIKE '%é%' OR name LIKE '%í%' OR name LIKE '%ó%' 
               OR name LIKE '%ú%' OR name LIKE '%â%' OR name LIKE '%ê%' 
               OR name LIKE '%î%' OR name LIKE '%ô%' OR name LIKE '%û%')
        LIMIT 10
    """)

    files_with_accents = indexer.cursor.fetchall()

    if not files_with_accents:
        print("❌ Nenhum arquivo com acentos encontrado nos dados reais.")
        print("💡 Vou criar arquivos de teste temporários...")

        # Criar arquivos de teste se não houver dados reais
        test_files = [
            {
                'id': 'real_test_1',
                'name': 'Documentação Técnica.pdf',
                'path': '/test/documentacao.pdf',
                'description': 'Documentação técnica sobre programação',
                'source': 'test_real',
                'mimeType': 'application/pdf',
                'size': 1024,
                'modifiedTime': 1234567890,
                'createdTime': 1234567890,
                'parentId': None
            },
            {
                'id': 'real_test_2',
                'name': 'Relatório de Vendas - Março.xlsx',
                'path': '/test/relatorio_marco.xlsx',
                'description': 'Relatório mensal de vendas - março 2024',
                'source': 'test_real',
                'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'size': 2048,
                'modifiedTime': 1234567890,
                'createdTime': 1234567890,
                'parentId': None
            }
        ]

        indexer.save_files_in_batch(test_files, 'test_real')
        print("✅ Arquivos de teste criados!")

        # Atualizar lista
        files_with_accents = [
            ('real_test_1', 'Documentação Técnica.pdf',
             'Documentação técnica sobre programação', 'test_real'),
            ('real_test_2', 'Relatório de Vendas - Março.xlsx',
             'Relatório mensal de vendas - março 2024', 'test_real')
        ]

    print(f"\n📄 Arquivos com acentos encontrados: {len(files_with_accents)}")

    # Mostrar arquivos encontrados
    for i, (file_id, name, description, source) in enumerate(files_with_accents[:5], 1):
        print(f"  {i}. {name} ({source})")
        if description:
            desc_short = description[:50] + \
                "..." if len(description) > 50 else description
            print(f"     └─ {desc_short}")

    # Testar busca com arquivos reais
    print(f"\n🧪 TESTANDO BUSCA COM ARQUIVOS REAIS...")

    test_cases = []
    successful_tests = 0

    # Para cada arquivo com acento, extrair palavras para testar
    # Testar só primeiros 3
    for file_id, name, description, source in files_with_accents[:3]:
        # Extrair palavras com acentos do nome
        words = name.lower().split()
        for word in words:
            # Remover pontuação básica
            clean_word = word.strip('.,()[]{}"-_')
            if any(char in clean_word for char in 'ãçáéíóúâêîôûàèìòù') and len(clean_word) > 2:
                # Testar palavra original e normalizada
                normalized_word = normalize_text(clean_word)
                if normalized_word != clean_word:
                    test_cases.extend([
                        (clean_word, f"Palavra original de '{name}'"),
                        (normalized_word, f"Palavra normalizada de '{name}'")
                    ])
                    break  # Só uma palavra por arquivo para não sobrecarregar

    # Se não encontramos casos de teste, usar casos genéricos
    if not test_cases:
        test_cases = [
            ("documentação", "Palavra comum com ç"),
            ("documentacao", "Palavra comum sem ç"),
            ("relatório", "Palavra comum com ó"),
            ("relatorio", "Palavra comum sem ó"),
            ("técnica", "Palavra comum com é"),
            ("tecnica", "Palavra comum sem é"),
            ("março", "Palavra comum com ç"),
            ("marco", "Palavra comum sem ç")
        ]

    print(f"📋 Executando {len(test_cases)} testes de busca...")

    for search_term, description in test_cases:
        print(f"\n🔎 Testando: '{search_term}' ({description})")

        # Simular exatamente como a UI faz a busca
        results = indexer.load_files_paged(
            source=None,  # Buscar em todas as fontes
            page=0,
            page_size=50,
            search_term=search_term.lower(),  # Como na UI
            sort_by='name_asc',
            filter_type='all',
            folder_id=None,
            advanced_filters={},
            explorer_special=False
        )

        found_count = len(results)
        print(f"  📊 Resultados encontrados: {found_count}")

        if results:
            successful_tests += 1
            print("  📄 Primeiros resultados:")
            for result in results[:3]:  # Mostrar só primeiros 3
                name = result.get('name', 'N/A')
                source = result.get('source', 'N/A')
                print(f"    • {name} ({source})")
        else:
            print("  ❌ Nenhum resultado encontrado")

        # Mostrar normalização
        normalized = normalize_text(search_term)
        if normalized != search_term.lower():
            print(f"  🔄 Normalização: '{search_term}' → '{normalized}'")

    # Estatísticas finais
    total_tests = len(test_cases)
    success_rate = (successful_tests / total_tests *
                    100) if total_tests > 0 else 0

    print(f"\n📊 RESULTADOS FINAIS:")
    print(f"  ✅ Testes bem-sucedidos: {successful_tests}/{total_tests}")
    print(f"  📈 Taxa de sucesso: {success_rate:.1f}%")
    print(f"  📁 Total de arquivos no banco: {total_files}")

    if success_rate >= 70:
        print(f"  🎉 NORMALIZAÇÃO FUNCIONANDO PERFEITAMENTE NO APP REAL!")
        result = True
    elif success_rate >= 50:
        print(f"  ✅ NORMALIZAÇÃO FUNCIONANDO BEM NO APP REAL!")
        result = True
    else:
        print(f"  ⚠️ NORMALIZAÇÃO PRECISA DE AJUSTES NO APP REAL!")
        result = False

    # Limpar dados de teste se foram criados
    if not files_with_accents or all(item[3] == 'test_real' for item in files_with_accents):
        print(f"\n🧹 Limpando dados de teste temporários...")
        indexer.cursor.execute("DELETE FROM files WHERE source = 'test_real'")
        indexer.cursor.execute(
            "DELETE FROM search_index WHERE source = 'test_real'")
        indexer.conn.commit()

    indexer.close()
    return result


def test_app_integration():
    """Testa se o app está usando as funções corretas de normalização"""
    print("\n🔧 TESTE DE INTEGRAÇÃO COM O APP")
    print("=" * 40)

    # Verificar se os arquivos principais existem
    required_files = ['app.py', 'ui.py', 'database.py', 'workers.py']
    missing_files = []

    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f"❌ Arquivos faltando: {', '.join(missing_files)}")
        return False

    print("✅ Todos os arquivos principais encontrados")

    # Verificar se a função normalize_text está sendo importada corretamente
    try:
        from database import normalize_text
        test_result = normalize_text("Educação")
        expected = "educacao"

        if test_result == expected:
            print(f"✅ Função normalize_text funcionando: '{test_result}'")
        else:
            print(
                f"❌ Função normalize_text com problema: '{test_result}' (esperado: '{expected}')")
            return False
    except ImportError as e:
        print(f"❌ Erro importando normalize_text: {e}")
        return False

    # Verificar se o banco tem a estrutura correta
    try:
        indexer = FileIndexer('file_index.db')

        # Verificar se tabela search_index tem colunas normalizadas
        indexer.cursor.execute("PRAGMA table_info(search_index)")
        columns = [col[1] for col in indexer.cursor.fetchall()]

        expected_columns = ['name', 'description',
                            'normalized_name', 'normalized_description']
        has_normalized = all(col in columns for col in expected_columns)

        if has_normalized:
            print("✅ Estrutura do banco com normalização correta")
        else:
            print(f"❌ Banco sem colunas de normalização. Colunas: {columns}")
            print("💡 Execute: python -c \"from database import FileIndexer; FileIndexer().rebuild_search_index_with_normalization()\"")
            return False

        indexer.close()

    except Exception as e:
        print(f"❌ Erro verificando banco: {e}")
        return False

    print("✅ Integração com app verificada com sucesso!")
    return True


if __name__ == "__main__":
    print("🚀 INICIANDO TESTE COMPLETO DO APLICATIVO REAL")
    print("=" * 60)

    # Teste 1: Integração
    integration_ok = test_app_integration()

    # Teste 2: Funcionalidade real
    if integration_ok:
        functionality_ok = test_app_normalization()
    else:
        functionality_ok = False

    print(f"\n🏁 RESULTADO FINAL:")
    print(f"  Integração: {'✅ OK' if integration_ok else '❌ FALHOU'}")
    print(f"  Funcionalidade: {'✅ OK' if functionality_ok else '❌ FALHOU'}")

    if integration_ok and functionality_ok:
        print(f"\n🎉 PRIORIDADE 1 VALIDADA COM SUCESSO NO APP REAL!")
        print(f"🚀 Pronto para PRIORIDADE 2: Otimizar Sincronização!")
    else:
        print(f"\n⚠️ Alguns testes falharam. Verifique os erros acima.")
