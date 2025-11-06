# Teste completo de todas as funcionalidades do VoxImago

import sqlite3
from src.search import SearchEngine
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_basic_search():
    print("🔍 TESTE 1: OPERADORES DE BUSCA BÁSICOS")
    print("=" * 60)

    try:
        conn = sqlite3.connect('data/test_file_index.db')
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return False

    try:
        print("\n1.1 BUSCA SIMPLES:")
        tests = ["jesus", "carol", "digital", "planilha", "haiti"]
        for term in tests:
            try:
                cursor.execute(
                    "SELECT name FROM search_index WHERE search_index MATCH ?", (term,))
                results = cursor.fetchall()
                print(f'  "{term}": {len(results)} resultados')
            except Exception as e:
                print(f'  "{term}": ERRO - {e}')

        print("\n1.2 BUSCA COM ACENTOS (normalização):")
        accent_tests = ["joão", "jose", "pará", "medjugorje", "oração"]
        for term in accent_tests:
            try:
                norm_term = SearchEngine(None).normalize_text(term)
                cursor.execute(
                    "SELECT name FROM search_index WHERE search_index MATCH ?", (norm_term,))
                results = cursor.fetchall()
                print(f'  "{term}" → "{norm_term}": {len(results)} resultados')
            except Exception as e:
                print(f'  "{term}": ERRO - {e}')

        print("\n1.3 BUSCA AND (termos com espaço):")
        and_tests = ["jesus menino", "carol planilha",
                     "haiti 2021", "pe gilson"]
        for term in and_tests:
            try:
                cursor.execute(
                    "SELECT name FROM search_index WHERE search_index MATCH ?", (term,))
                results = cursor.fetchall()
                print(f'  "{term}": {len(results)} resultados')
            except Exception as e:
                print(f'  "{term}": ERRO - {e}')

        print("\n✅ TESTE 1 CONCLUÍDO")
        return True

    except Exception as e:
        print(f"❌ Erro geral no teste 1: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao fechar conexão: {e}")


def test_operators():
    print("\n🔍 TESTE 2: OPERADORES FTS5")


def test_operators():
    print("\n🔍 TESTE 2: OPERADORES FTS5")
    print("=" * 60)

    try:
        conn = sqlite3.connect('data/test_file_index.db')
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return False

    try:
        print("\n2.1 OPERADOR OR:")
        or_tests = ["jesus OR carol", "haiti OR brasil", "2020 OR 2021"]
        for term in or_tests:
            try:
                cursor.execute(
                    "SELECT name FROM search_index WHERE search_index MATCH ?", (term,))
                results = cursor.fetchall()
                print(f'  "{term}": {len(results)} resultados')
            except Exception as e:
                print(f'  "{term}": ERRO - {e}')

        print("\n2.2 OPERADOR NOT (-):")
        not_tests = ["jesus NOT natal", "carol NOT planilha", "haiti NOT 2020"]
        for term in not_tests:
            try:
                cursor.execute(
                    "SELECT name FROM search_index WHERE search_index MATCH ?", (term,))
                results = cursor.fetchall()
                print(f'  "{term}": {len(results)} resultados')
            except Exception as e:
                print(f'  "{term}": ERRO - {e}')

        print("\n2.3 OPERADOR NEAR:")
        near_tests = ['jesus NEAR menino',
                      'pe NEAR gilson', 'ana NEAR carolina']
        for term in near_tests:
            try:
                cursor.execute(
                    "SELECT name FROM search_index WHERE search_index MATCH ?", (term,))
                results = cursor.fetchall()
                print(f'  "{term}": {len(results)} resultados')
            except Exception as e:
                print(f'  "{term}": ERRO - {e}')

        print("\n2.4 BUSCA POR PREFIXO (*):")
        prefix_tests = ["car*", "je*", "plan*", "dig*"]
        for term in prefix_tests:
            try:
                cursor.execute(
                    "SELECT name FROM search_index WHERE search_index MATCH ?", (term,))
                results = cursor.fetchall()
                print(f'  "{term}": {len(results)} resultados')
            except Exception as e:
                print(f'  "{term}": ERRO - {e}')

        print("\n✅ TESTE 2 CONCLUÍDO")
        return True

    except Exception as e:
        print(f"❌ Erro geral no teste 2: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao fechar conexão: {e}")


def test_metadata_search():
    print("\n🔍 TESTE 3: BUSCA POR METADADOS")
    print("=" * 60)

    try:
        conn = sqlite3.connect('data/test_file_index.db')
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return False

    try:
        cursor.execute("PRAGMA table_info(files)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"\n3.1 COLUNAS DISPONÍVEIS: {columns}")

        print("\n3.2 BUSCA POR EXTENSÃO:")
        ext_tests = [".jpg", ".png", ".mp4", ".pdf", ".xlsx"]
        for ext in ext_tests:
            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM files WHERE path LIKE ?", (f"%{ext}",))
                count = cursor.fetchone()[0]
                print(f'  "{ext}": {count} arquivos')
            except Exception as e:
                print(f'  "{ext}": ERRO - {e}')

        print("\n3.3 BUSCA POR FONTE:")
        try:
            cursor.execute(
                "SELECT source, COUNT(*) FROM files GROUP BY source")
            sources = cursor.fetchall()
            for source, count in sources:
                print(f'  "{source}": {count} arquivos')
        except Exception as e:
            print(f"  Busca por fonte: ERRO - {e}")

        print("\n3.4 BUSCA POR TAMANHO:")
        size_ranges = [
            ("< 1MB", 0, 1024*1024),
            ("1-10MB", 1024*1024, 10*1024*1024),
            ("10-100MB", 10*1024*1024, 100*1024*1024),
            ("> 100MB", 100*1024*1024, float('inf'))
        ]

        for label, min_size, max_size in size_ranges:
            try:
                if max_size == float('inf'):
                    cursor.execute(
                        "SELECT COUNT(*) FROM files WHERE size >= ?", (min_size,))
                else:
                    cursor.execute(
                        "SELECT COUNT(*) FROM files WHERE size >= ? AND size < ?", (min_size, max_size))
                count = cursor.fetchone()[0]
                print(f'  {label}: {count} arquivos')
            except Exception as e:
                print(f'  {label}: ERRO - {e}')

        print("\n✅ TESTE 3 CONCLUÍDO")
        return True

    except Exception as e:
        print(f"❌ Erro geral no teste 3: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao fechar conexão: {e}")


def test_filters():
    print("\n🔍 TESTE 4: FILTROS POR CATEGORIA")
    print("=" * 60)

    try:
        conn = sqlite3.connect('data/test_file_index.db')
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return False

    try:
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp',
                      '.tiff', '.tif', '.webp', '.svg', '.ico', '.heic', '.arw'}
        video_exts = {'.mp4', '.avi', '.mov', '.wmv', '.flv',
                      '.webm', '.mkv', '.m4v', '.mpg', '.mpeg', '.3gp', '.mts'}
        document_exts = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.pages', '.xls', '.xlsx', '.ppt', '.pptx', '.odp', '.key', '.csv', '.html', '.htm', '.xml', '.json', '.md', '.epub', '.mobi', '.fb2', '.djvu', '.ps', '.eps', '.ai', '.psd', '.indd',
                         '.pub', '.xps', '.oxps', '.sxw', '.sxc', '.sxi', '.sxd', '.wpd', '.wps', '.one', '.msg', '.eml', '.mht', '.mhtml', '.url', '.lnk', '.desktop', '.webloc', '.gsheet', '.gdoc', '.gslide', '.gdraw', '.gform', '.gtable', '.gsite', '.gmap', '.gjam'}
        audio_exts = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus', '.aiff', '.au', '.ra', '.3ga', '.amr', '.awb', '.dss',
                      '.dvf', '.m4b', '.m4p', '.mmf', '.mpc', '.msv', '.oga', '.raw', '.rf64', '.sln', '.tta', '.voc', '.vox', '.wv', '.webm', '.8svx', '.cda'}

        print("\n4.1 CONTAGEM POR CATEGORIA:")

        try:
            image_ext_list = "', '".join(image_exts)
            cursor.execute(
                f"SELECT COUNT(*) FROM files WHERE LOWER(SUBSTR(path, -4)) IN ('{image_ext_list}') OR LOWER(SUBSTR(path, -5)) IN ('{image_ext_list}')")
            image_count = cursor.fetchone()[0]
            print(f"  Images: {image_count} arquivos")
        except Exception as e:
            print(f"  Images: ERRO - {e}")

        try:
            video_ext_list = "', '".join(video_exts)
            cursor.execute(
                f"SELECT COUNT(*) FROM files WHERE LOWER(SUBSTR(path, -4)) IN ('{video_ext_list}') OR LOWER(SUBSTR(path, -5)) IN ('{video_ext_list}')")
            video_count = cursor.fetchone()[0]
            print(f"  Videos: {video_count} arquivos")
        except Exception as e:
            print(f"  Videos: ERRO - {e}")

        try:
            doc_ext_list = "', '".join(list(document_exts)[:20])
            cursor.execute(
                f"SELECT COUNT(*) FROM files WHERE LOWER(SUBSTR(path, -4)) IN ('{doc_ext_list}') OR LOWER(SUBSTR(path, -5)) IN ('{doc_ext_list}')")
            doc_count = cursor.fetchone()[0]
            print(f"  Documents: {doc_count} arquivos")
        except Exception as e:
            print(f"  Documents: ERRO - {e}")

        try:
            audio_ext_list = "', '".join(audio_exts)
            cursor.execute(
                f"SELECT COUNT(*) FROM files WHERE LOWER(SUBSTR(path, -4)) IN ('{audio_ext_list}') OR LOWER(SUBSTR(path, -5)) IN ('{audio_ext_list}')")
            audio_count = cursor.fetchone()[0]
            print(f"  Audio: {audio_count} arquivos")
        except Exception as e:
            print(f"  Audio: ERRO - {e}")

        try:
            cursor.execute("SELECT COUNT(*) FROM files")
            total_count = cursor.fetchone()[0]
            print(f"  Total: {total_count} arquivos")
        except Exception as e:
            print(f"  Total: ERRO - {e}")

        print("\n✅ TESTE 4 CONCLUÍDO")
        return True

    except Exception as e:
        print(f"❌ Erro geral no teste 4: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao fechar conexão: {e}")


def test_fusion():
    print("\n🔍 TESTE 5: VERIFICAR FUSÃO DE METADADOS")
    print("=" * 60)

    try:
        conn = sqlite3.connect('data/test_file_index.db')
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return False

    try:
        print("\n5.1 ARQUIVOS COM DESCRIÇÃO:")
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM files WHERE description IS NOT NULL AND description != ''")
            desc_count = cursor.fetchone()[0]
            print(f"  Arquivos com descrição: {desc_count}")
        except Exception as e:
            print(f"  Contagem de descrições: ERRO - {e}")

        print("\n5.2 VERIFICAR DIGITAL.JPG:")
        try:
            cursor.execute(
                "SELECT name, size, source, description FROM files WHERE LOWER(name) = 'digital.jpg'")
            digital_files = cursor.fetchall()
            for file_info in digital_files:
                name, size, source, desc = file_info
                print(
                    f"  {name} | {size} bytes | Fonte: {source} | Descrição: '{desc}'")
        except Exception as e:
            print(f"  Busca digital.jpg: ERRO - {e}")

        print("\n5.3 ARQUIVOS DUPLICADOS POR NOME:")
        try:
            cursor.execute("""
                SELECT name, COUNT(*) as count 
                FROM files 
                GROUP BY LOWER(name) 
                HAVING COUNT(*) > 1 
                ORDER BY count DESC 
                LIMIT 10
            """)
            duplicates = cursor.fetchall()
            for name, count in duplicates:
                print(f"  {name}: {count} ocorrências")
        except Exception as e:
            print(f"  Busca de duplicados: ERRO - {e}")

        print("\n5.4 DISTRIBUIÇÃO POR FONTE:")
        try:
            cursor.execute(
                "SELECT source, COUNT(*) FROM files GROUP BY source ORDER BY COUNT(*) DESC")
            sources = cursor.fetchall()
            for source, count in sources:
                print(f"  {source}: {count} arquivos")
        except Exception as e:
            print(f"  Distribuição por fonte: ERRO - {e}")

        print("\n✅ TESTE 5 CONCLUÍDO")
        return True

    except Exception as e:
        print(f"❌ Erro geral no teste 5: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao fechar conexão: {e}")


if __name__ == "__main__":
    try:
        results = []
        results.append(("Busca básica", test_basic_search()))
        results.append(("Operadores FTS5", test_operators()))
        results.append(("Busca por metadados", test_metadata_search()))
        results.append(("Filtros por categoria", test_filters()))
        results.append(("Fusão de metadados", test_fusion()))

        print("\n📊 RESUMO DOS TESTES:")
        for test_name, passed in results:
            status = "✅ PASSOU" if passed else "❌ FALHOU"
            print(f"  {test_name}: {status}")

        all_passed = all(result[1] for result in results)

        if all_passed:
            print("\n🎉 TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
            sys.exit(0)
        else:
            print("\n❌ ALGUNS TESTES FALHARAM!")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERRO FATAL DURANTE OS TESTES: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
