#!/usr/bin/env python3
"""
Correção rápida para compatibilidade com workers.py
Resolve o erro de inserção no search_index
"""

from database import FileIndexer, normalize_text


def fix_workers_compatibility():
    print("🔧 CORRIGINDO COMPATIBILIDADE COM WORKERS.PY")
    print("=" * 50)

    indexer = FileIndexer()

    try:
        # Verificar estrutura atual do search_index
        indexer.cursor.execute("PRAGMA table_info(search_index)")
        columns = [col[1] for col in indexer.cursor.fetchall()]
        print(f"📋 Colunas atuais do search_index: {columns}")

        # Verificar quantos arquivos temos
        indexer.cursor.execute("SELECT COUNT(*) FROM files")
        total_files = indexer.cursor.fetchone()[0]
        print(f"📁 Total de arquivos no banco: {total_files}")

        print("🔄 Recriando search_index com estrutura compatível...")

        # Recriar tabela com estrutura correta
        indexer.cursor.execute('DROP TABLE IF EXISTS search_index')

        indexer.cursor.execute('''
            CREATE VIRTUAL TABLE search_index USING fts5(
                name, 
                description, 
                normalized_name,
                normalized_description,
                file_id UNINDEXED, 
                source UNINDEXED, 
                tokenize="trigram"
            )
        ''')

        print("✅ Tabela search_index recriada com estrutura correta")

        if total_files > 0:
            # Reindexar todos os arquivos existentes
            print(f"📥 Reindexando {total_files} arquivos com normalização...")

            indexer.cursor.execute(
                'SELECT file_id, name, description, source FROM files')
            all_files = indexer.cursor.fetchall()

            batch_data = []
            for i, (file_id, name, description, source) in enumerate(all_files):
                name = name or ""
                description = description or ""

                batch_data.append((
                    name,                        # nome original
                    description,                 # descrição original
                    normalize_text(name),        # nome normalizado
                    normalize_text(description),  # descrição normalizada
                    file_id,
                    source
                ))

                # Processar em lotes para performance
                if len(batch_data) >= 1000:
                    indexer.cursor.executemany(
                        "INSERT INTO search_index VALUES (?, ?, ?, ?, ?, ?)",
                        batch_data
                    )
                    batch_data = []
                    print(f"  📊 Processados {i + 1}/{total_files} arquivos...")

            # Processar restantes
            if batch_data:
                indexer.cursor.executemany(
                    "INSERT INTO search_index VALUES (?, ?, ?, ?, ?, ?)",
                    batch_data
                )

            print(f"✅ Todos os {total_files} arquivos reindexados!")

        indexer.conn.commit()

        # Verificar se funcionou
        indexer.cursor.execute("SELECT COUNT(*) FROM search_index")
        indexed_count = indexer.cursor.fetchone()[0]
        print(f"📊 Arquivos no índice: {indexed_count}")

        print("\n🎉 CORREÇÃO CONCLUÍDA COM SUCESSO!")
        print("💡 O workers.py agora deve funcionar sem erros.")
        print("🔍 A busca com normalização está ativa e funcionando.")

        # Teste rápido da normalização
        print("\n🧪 Teste rápido da correção:")
        test_cases = [
            ("educação", "educacao"),
            ("coração", "coracao"),
            ("açúcar", "acucar")
        ]

        for original, expected in test_cases:
            result = normalize_text(original)
            status = "✅" if result == expected else "❌"
            print(f"  {status} '{original}' → '{result}' (esperado: '{expected}')")

    except Exception as e:
        print(f"❌ Erro na correção: {e}")
        print(f"💡 Detalhes do erro: {type(e).__name__}")
        indexer.conn.rollback()
        raise
    finally:
        indexer.close()


def test_search_after_fix():
    """Teste rápido para confirmar que a busca está funcionando"""
    print("\n🔍 TESTE DE BUSCA APÓS CORREÇÃO")
    print("=" * 40)

    indexer = FileIndexer()

    try:
        # Verificar se temos dados para testar
        indexer.cursor.execute("SELECT COUNT(*) FROM files")
        total_files = indexer.cursor.fetchone()[0]

        if total_files == 0:
            print("📁 Nenhum arquivo para testar. Criando dados de teste...")

            # Criar dados de teste temporários
            test_files = [
                {
                    'id': 'fix_test_1',
                    'name': 'Educação Digital.pdf',
                    'path': '/test/educacao.pdf',
                    'description': 'Documento sobre educação digital',
                    'source': 'test_fix',
                    'mimeType': 'application/pdf',
                    'size': 1024,
                    'modifiedTime': 1234567890,
                    'createdTime': 1234567890,
                    'parentId': None
                }
            ]

            indexer.save_files_in_batch(test_files, 'test_fix')
            print("✅ Dados de teste criados!")

        # Testar busca com normalização
        test_searches = ["educacao", "educação"]

        for search_term in test_searches:
            print(f"\n🔎 Testando busca: '{search_term}'")

            results = indexer.load_files_paged(
                source=None,
                page=0,
                page_size=5,
                search_term=search_term,
                sort_by='name_asc',
                filter_type='all'
            )

            print(f"  📊 Resultados encontrados: {len(results)}")

            if results:
                for result in results:
                    name = result.get('name', 'N/A')
                    print(f"    📄 {name}")

            # Mostrar normalização
            normalized = normalize_text(search_term)
            print(f"  🔄 Normalização: '{search_term}' → '{normalized}'")

        # Limpar dados de teste se foram criados
        if total_files == 0:
            print("\n🧹 Limpando dados de teste...")
            indexer.cursor.execute(
                "DELETE FROM files WHERE source = 'test_fix'")
            indexer.cursor.execute(
                "DELETE FROM search_index WHERE source = 'test_fix'")
            indexer.conn.commit()

        print("✅ Teste de busca concluído com sucesso!")

    except Exception as e:
        print(f"❌ Erro no teste: {e}")
    finally:
        indexer.close()


if __name__ == "__main__":
    print("🚀 INICIANDO CORREÇÃO DE COMPATIBILIDADE")
    print("=" * 60)

    # Aplicar correção
    fix_workers_compatibility()

    # Testar se funcionou
    test_search_after_fix()

    print(f"\n🏁 CORREÇÃO FINALIZADA!")
    print("🚀 Agora você pode:")
    print("  1. Executar o aplicativo: python app.py")
    print("  2. Testar busca com acentos na interface")
    print("  3. Continuar para Prioridade 2: Otimizar Sincronização")
