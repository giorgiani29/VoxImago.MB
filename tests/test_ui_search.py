# Teste de busca com normalização de texto na interface do usuário.

from database import FileIndexer, normalize_text
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_ui_search_simulation():
    print("🔍 TESTE DE BUSCA DA INTERFACE")
    print("=" * 50)

    indexer = FileIndexer()

    test_searches = [
        "açúcar",
        "acucar",
        "coração",
        "coracao",
        "opção",
        "opcao",
        "educação",
        "educacao",
        "São Paulo",
        "sao paulo",
    ]

    print("📁 Adicionando arquivos de teste...")

    test_files = [
        {
            'id': 'test_ui_1',
            'name': 'Receitas de Açúcar.pdf',
            'path': '/test/receitas_acucar.pdf',
            'description': 'Receitas doces com açúcar refinado',
            'source': 'test',
            'mimeType': 'application/pdf',
            'size': 1024,
            'modifiedTime': 1234567890,
            'createdTime': 1234567890,
            'parentId': None
        },
        {
            'id': 'test_ui_2',
            'name': 'Coração Valente - Filme.mkv',
            'path': '/test/coracao_valente.mkv',
            'description': 'Filme épico sobre corações valentes',
            'source': 'test',
            'mimeType': 'video/x-matroska',
            'size': 2048000,
            'modifiedTime': 1234567890,
            'createdTime': 1234567890,
            'parentId': None
        },
        {
            'id': 'test_ui_3',
            'name': 'Opções Educacionais 2024.docx',
            'path': '/test/opcoes_educacao.docx',
            'description': 'Documento sobre opções de educação superior',
            'source': 'test',
            'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'size': 4096,
            'modifiedTime': 1234567890,
            'createdTime': 1234567890,
            'parentId': None
        }
    ]

    indexer.save_files_in_batch(test_files, 'test')

    print("\n🧪 Testando buscas como na interface...")

    for search_term in test_searches:
        print(f"\n🔎 Simulando busca: '{search_term}'")
        ui_search_term = search_term.lower()

        results = indexer.load_files_paged(
            source=None,
            page=0,
            page_size=50,
            search_term=ui_search_term,
            sort_by='name_asc',
            filter_type='all',
            folder_id=None,
            advanced_filters={},
            explorer_special=False
        )

        print(f"📊 Resultados encontrados: {len(results)}")

        if results:
            print("  📄 Arquivos encontrados:")
            for result in results:
                name = result.get('name', 'N/A')
                desc = result.get('description', 'N/A')
                print(f"    • {name}")
                print(f"      └─ {desc}")
        else:
            print("  ❌ Nenhum resultado encontrado")

        normalized = normalize_text(search_term)
        if normalized != search_term.lower():
            print(f"  🔄 Normalização: '{search_term}' → '{normalized}'")

    print("\n🧹 Limpando dados de teste...")
    for test_file in test_files:
        indexer.cursor.execute(
            "DELETE FROM files WHERE file_id = ?", (test_file['id'],))
        indexer.cursor.execute(
            "DELETE FROM search_index WHERE file_id = ?", (test_file['id'],))
    indexer.conn.commit()

    indexer.close()
    print("✅ Teste da interface concluído!")


if __name__ == "__main__":
    test_ui_search_simulation()
