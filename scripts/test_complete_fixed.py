#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste completo de todas as funcionalidades do VoxImago
"""

from database import normalize_text
import sqlite3
import os
import sys
sys.path.append('src')


def test_basic_search():
    """Teste 1: Operadores de busca básicos"""
    print("🔍 TESTE 1: OPERADORES DE BUSCA BÁSICOS")
    print("=" * 60)

    conn = sqlite3.connect('data/file_index.db')
    cursor = conn.cursor()

    # 1.1 Busca simples
    print("\n1.1 BUSCA SIMPLES:")
    tests = ["jesus", "carol", "digital", "planilha", "haiti"]
    for term in tests:
        cursor.execute(
            "SELECT path FROM search_index WHERE search_index MATCH ?", (term,))
        results = cursor.fetchall()
        print(f'  "{term}": {len(results)} resultados')

    # 1.2 Busca com acentos
    print("\n1.2 BUSCA COM ACENTOS (normalização):")
    accent_tests = ["joão", "jose", "pará", "medjugorje", "oração"]
    for term in accent_tests:
        norm_term = normalize_text(term)
        cursor.execute(
            "SELECT path FROM search_index WHERE search_index MATCH ?", (norm_term,))
        results = cursor.fetchall()
        print(f'  "{term}" → "{norm_term}": {len(results)} resultados')

    # 1.3 Busca AND (espaço)
    print("\n1.3 BUSCA AND (termos com espaço):")
    and_tests = ["jesus menino", "carol planilha", "haiti 2021", "pe gilson"]
    for term in and_tests:
        cursor.execute(
            "SELECT path FROM search_index WHERE search_index MATCH ?", (term,))
        results = cursor.fetchall()
        print(f'  "{term}": {len(results)} resultados')

    conn.close()
    print("\n✅ TESTE 1 CONCLUÍDO")


def test_operators():
    """Teste 2: Operadores FTS5"""
    print("\n🔍 TESTE 2: OPERADORES FTS5")
    print("=" * 60)

    conn = sqlite3.connect('data/file_index.db')
    cursor = conn.cursor()

    # 2.1 Operador OR
    print("\n2.1 OPERADOR OR:")
    or_tests = ["jesus OR carol", "haiti OR brasil", "2020 OR 2021"]
    for term in or_tests:
        try:
            cursor.execute(
                "SELECT path FROM search_index WHERE search_index MATCH ?", (term,))
            results = cursor.fetchall()
            print(f'  "{term}": {len(results)} resultados')
        except Exception as e:
            print(f'  "{term}": ERRO - {e}')

    # 2.2 Operador NOT (-)
    print("\n2.2 OPERADOR NOT (-):")
    not_tests = ["jesus NOT natal", "carol NOT planilha", "haiti NOT 2020"]
    for term in not_tests:
        try:
            cursor.execute(
                "SELECT path FROM search_index WHERE search_index MATCH ?", (term,))
            results = cursor.fetchall()
            print(f'  "{term}": {len(results)} resultados')
        except Exception as e:
            print(f'  "{term}": ERRO - {e}')

    # 2.3 Operador NEAR
    print("\n2.3 OPERADOR NEAR:")
    near_tests = ['jesus NEAR menino', 'pe NEAR gilson', 'ana NEAR carolina']
    for term in near_tests:
        try:
            cursor.execute(
                "SELECT path FROM search_index WHERE search_index MATCH ?", (term,))
            results = cursor.fetchall()
            print(f'  "{term}": {len(results)} resultados')
        except Exception as e:
            print(f'  "{term}": ERRO - {e}')

    # 2.4 Prefixo (*)
    print("\n2.4 BUSCA POR PREFIXO (*):")
    prefix_tests = ["car*", "je*", "plan*", "dig*"]
    for term in prefix_tests:
        try:
            cursor.execute(
                "SELECT path FROM search_index WHERE search_index MATCH ?", (term,))
            results = cursor.fetchall()
            print(f'  "{term}": {len(results)} resultados')
        except Exception as e:
            print(f'  "{term}": ERRO - {e}')

    conn.close()
    print("\n✅ TESTE 2 CONCLUÍDO")


def test_metadata_search():
    """Teste 3: Busca por metadados"""
    print("\n🔍 TESTE 3: BUSCA POR METADADOS")
    print("=" * 60)

    conn = sqlite3.connect('data/file_index.db')
    cursor = conn.cursor()

    # 3.1 Verificar estrutura da tabela files
    cursor.execute("PRAGMA table_info(files)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"\n3.1 COLUNAS DISPONÍVEIS: {columns}")

    # 3.2 Buscar por extensão
    print("\n3.2 BUSCA POR EXTENSÃO:")
    ext_tests = [".jpg", ".png", ".mp4", ".pdf", ".xlsx"]
    for ext in ext_tests:
        cursor.execute(
            "SELECT COUNT(*) FROM files WHERE path LIKE ?", (f"%{ext}",))
        count = cursor.fetchone()[0]
        print(f'  "{ext}": {count} arquivos')

    # 3.3 Buscar por fonte
    print("\n3.3 BUSCA POR FONTE:")
    cursor.execute("SELECT source, COUNT(*) FROM files GROUP BY source")
    sources = cursor.fetchall()
    for source, count in sources:
        print(f'  "{source}": {count} arquivos')

    # 3.4 Buscar por tamanho
    print("\n3.4 BUSCA POR TAMANHO:")
    size_ranges = [
        ("< 1MB", 0, 1024*1024),
        ("1-10MB", 1024*1024, 10*1024*1024),
        ("10-100MB", 10*1024*1024, 100*1024*1024),
        ("> 100MB", 100*1024*1024, float('inf'))
    ]

    for label, min_size, max_size in size_ranges:
        if max_size == float('inf'):
            cursor.execute(
                "SELECT COUNT(*) FROM files WHERE size >= ?", (min_size,))
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM files WHERE size >= ? AND size < ?", (min_size, max_size))
        count = cursor.fetchone()[0]
        print(f'  {label}: {count} arquivos')

    conn.close()
    print("\n✅ TESTE 3 CONCLUÍDO")


def test_filters():
    """Teste 4: Filtros por categoria"""
    print("\n🔍 TESTE 4: FILTROS POR CATEGORIA")
    print("=" * 60)

    conn = sqlite3.connect('data/file_index.db')
    cursor = conn.cursor()

    # Definir mapeamentos de extensão como no código original
    image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp',
                  '.tiff', '.tif', '.webp', '.svg', '.ico', '.heic', '.arw']
    video_exts = ['.mp4', '.avi', '.mov', '.wmv', '.flv',
                  '.webm', '.mkv', '.m4v', '.mpg', '.mpeg', '.3gp', '.mts']
    document_exts = ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt',
                     '.pages', '.xls', '.xlsx', '.ppt', '.pptx', '.gdoc', '.gsheet']
    audio_exts = ['.mp3', '.wav', '.flac',
                  '.aac', '.ogg', '.wma', '.m4a', '.opus']

    # 4.1 Contar por categoria
    print("\n4.1 CONTAGEM POR CATEGORIA:")

    categories = [
        ("Images", image_exts),
        ("Videos", video_exts),
        ("Documents", document_exts),
        ("Audio", audio_exts)
    ]

    for cat_name, exts in categories:
        conditions = []
        for ext in exts:
            conditions.append(f"LOWER(path) LIKE '%{ext}'")

        if conditions:
            query = f"SELECT COUNT(*) FROM files WHERE {' OR '.join(conditions)}"
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"  {cat_name}: {count} arquivos")

    # Total
    cursor.execute("SELECT COUNT(*) FROM files")
    total_count = cursor.fetchone()[0]
    print(f"  Total: {total_count} arquivos")

    conn.close()
    print("\n✅ TESTE 4 CONCLUÍDO")


def test_fusion():
    """Teste 5: Verificar fusão de metadados"""
    print("\n🔍 TESTE 5: VERIFICAR FUSÃO DE METADADOS")
    print("=" * 60)

    conn = sqlite3.connect('data/file_index.db')
    cursor = conn.cursor()

    # 5.1 Verificar arquivos com descrição
    print("\n5.1 ARQUIVOS COM DESCRIÇÃO:")
    cursor.execute(
        "SELECT COUNT(*) FROM files WHERE description IS NOT NULL AND description != ''")
    desc_count = cursor.fetchone()[0]
    print(f"  Arquivos com descrição: {desc_count}")

    # 5.2 Verificar digital.jpg especificamente
    print("\n5.2 VERIFICAR DIGITAL.JPG:")
    cursor.execute(
        "SELECT name, size, source, description FROM files WHERE LOWER(name) = 'digital.jpg'")
    digital_files = cursor.fetchall()
    for file_info in digital_files:
        name, size, source, desc = file_info
        print(f"  {name} | {size} bytes | Fonte: {source} | Descrição: '{desc}'")

    if not digital_files:
        print("  ❌ digital.jpg não encontrado!")

    # 5.3 Verificar arquivos duplicados por nome
    print("\n5.3 ARQUIVOS DUPLICADOS POR NOME:")
    cursor.execute("""
        SELECT name, COUNT(*) as count 
        FROM files 
        GROUP BY LOWER(name) 
        HAVING COUNT(*) > 1 
        ORDER BY count DESC 
        LIMIT 10
    """)
    duplicates = cursor.fetchall()
    if duplicates:
        for name, count in duplicates:
            print(f"  {name}: {count} ocorrências")
    else:
        print("  Nenhum arquivo duplicado por nome encontrado")

    # 5.4 Verificar fonte dos arquivos
    print("\n5.4 DISTRIBUIÇÃO POR FONTE:")
    cursor.execute(
        "SELECT source, COUNT(*) FROM files GROUP BY source ORDER BY COUNT(*) DESC")
    sources = cursor.fetchall()
    for source, count in sources:
        print(f"  {source}: {count} arquivos")

    conn.close()
    print("\n✅ TESTE 5 CONCLUÍDO")


def test_code_analysis():
    """Teste 6: Análise de código - duplicações e funções não usadas"""
    print("\n🔍 TESTE 6: ANÁLISE DE CÓDIGO")
    print("=" * 60)

    import ast
    import glob

    # Coletar todas as funções definidas
    all_functions = {}
    all_classes = {}
    function_calls = set()

    python_files = glob.glob("src/*.py") + ["app.py"]

    for file_path in python_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                    # Analisar AST
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            all_functions[node.name] = file_path
                        elif isinstance(node, ast.ClassDef):
                            all_classes[node.name] = file_path
                        elif isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name):
                                function_calls.add(node.func.id)
                            elif isinstance(node.func, ast.Attribute):
                                function_calls.add(node.func.attr)
            except Exception as e:
                print(f"  ⚠️  Erro analisando {file_path}: {e}")

    print(f"\n6.1 FUNÇÕES DEFINIDAS: {len(all_functions)}")
    print(f"6.2 CLASSES DEFINIDAS: {len(all_classes)}")
    print(f"6.3 CHAMADAS DE FUNÇÃO ENCONTRADAS: {len(function_calls)}")

    # Buscar funções potencialmente não usadas
    print("\n6.4 FUNÇÕES POTENCIALMENTE NÃO UTILIZADAS:")
    unused_functions = []
    for func_name, file_path in all_functions.items():
        # Ignorar métodos especiais e main
        if not func_name.startswith('_') and func_name != 'main':
            if func_name not in function_calls:
                unused_functions.append((func_name, file_path))

    if unused_functions:
        for func_name, file_path in unused_functions[:10]:  # Top 10
            print(f"  {func_name} em {file_path}")
    else:
        print("  Todas as funções parecem estar em uso")

    # Buscar imports duplicados
    print("\n6.5 VERIFICANDO IMPORTS...")
    import_counts = {}
    for file_path in python_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()
                        if line.startswith('import ') or line.startswith('from '):
                            import_counts[line] = import_counts.get(
                                line, 0) + 1
            except Exception as e:
                print(f"  ⚠️  Erro lendo {file_path}: {e}")

    # Mostrar imports mais comuns
    common_imports = sorted(import_counts.items(),
                            key=lambda x: x[1], reverse=True)[:5]
    for import_line, count in common_imports:
        print(f"  '{import_line}': usado {count} vezes")

    print("\n✅ TESTE 6 CONCLUÍDO")


if __name__ == "__main__":
    try:
        test_basic_search()
        test_operators()
        test_metadata_search()
        test_filters()
        test_fusion()
        test_code_analysis()

        print("\n" + "="*80)
        print("🎉 TODOS OS TESTES CONCLUÍDOS!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ ERRO DURANTE OS TESTES: {e}")
        import traceback
        traceback.print_exc()
