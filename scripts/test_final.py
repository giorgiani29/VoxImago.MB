#!/usr/bin/env python
import os
import sys
import sqlite3
print("\n📋 TESTE 1: BUSCA FTS5 BÁSICA")
print("\n📊 TESTE 3: METADADOS E FILTROS")
print("-" * 50)
"""Teste completo das funcionalidades do VoxImago"""

sys.path.append('src')


def run_all_tests():
    print("🧪 TESTE COMPLETO DE FUNCIONALIDADES VOXMAGO")
    print("=" * 70)

    conn = sqlite3.connect('data/test_file_index.db')
    cursor = conn.cursor()

    print("\n📊 ESTRUTURA DO BANCO:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"  Tabelas: {tables}")

    # Teste 1: Busca FTS5 básica
    print("\n🔍 TESTE 1: BUSCA FTS5 BÁSICA")
    print("-" * 50)

    search_terms = ["jesus", "carol", "digital",
                    "planilha", "haiti", "pe", "gilson"]

    for term in search_terms:
        cursor.execute(
            "SELECT name FROM search_index WHERE search_index MATCH ?", (term,))
        results = cursor.fetchall()
        print(f"  '{term}': {len(results)} resultados")
        if len(results) > 0 and len(results) <= 3:
            for r in results[:3]:
                print(f"    → {r[0]}")

    print("\n🔍 TESTE 2: OPERADORES FTS5")
    print("-" * 50)

    operators = [
        ("jesus OR carol", "Operador OR"),
        ("jesus NOT natal", "Operador NOT"),
        ("jesus AND menino", "Operador AND"),
        ("car*", "Prefixo"),
        ("\"jesus menino\"", "Frase exata")
    ]

    for query, desc in operators:
        try:
            cursor.execute(
                "SELECT name FROM search_index WHERE search_index MATCH ?", (query,))
            results = cursor.fetchall()
            print(f"  {desc}: '{query}' → {len(results)} resultados")
        except Exception as e:
            print(f"  {desc}: '{query}' → ERRO: {str(e)[:50]}")

    # Teste 3: Metadados e filtros
    print("\n🔍 TESTE 3: METADADOS E FILTROS")
    print("-" * 50)

    cursor.execute("SELECT source, COUNT(*) FROM files GROUP BY source")
    sources = cursor.fetchall()
    print("  Por fonte:")
    for source, count in sources:
        print(f"    {source}: {count} arquivos")
    cursor.execute("""
        SELECT 
            CASE 
                WHEN path LIKE '%.jpg' THEN '.jpg'
                WHEN path LIKE '%.png' THEN '.png'
                WHEN path LIKE '%.mp4' THEN '.mp4'
                WHEN path LIKE '%.pdf' THEN '.pdf'
                WHEN path LIKE '%.xlsx' THEN '.xlsx'
                WHEN path LIKE '%.jpeg' THEN '.jpeg'
                WHEN path LIKE '%.mov' THEN '.mov'
                WHEN path LIKE '%.docx' THEN '.docx'
                ELSE 'outros'
            END as ext,
            COUNT(*) as count 
        FROM files 
        WHERE path LIKE '%.%'
        GROUP BY ext 
        ORDER BY count DESC 
        LIMIT 10
    """)
    exts = cursor.fetchall()
    print("\n  Top 10 extensões:")
    for ext, count in exts:
        print(f"    {ext}: {count} arquivos")

    # Teste 4: Verificar fusão
    print("\n🔍 TESTE 4: VERIFICAR FUSÃO DE METADADOS")
    print("-" * 50)

    cursor.execute(
        "SELECT COUNT(*) FROM files WHERE description IS NOT NULL AND description != ''")
    desc_count = cursor.fetchone()[0]
    print(f"  Arquivos com descrição: {desc_count}")

    # Verificar digital.jpg especificamente
    cursor.execute(
        "SELECT name, size, source, description FROM files WHERE LOWER(name) LIKE '%digital%'")
    digital_files = cursor.fetchall()
    print(f"  Arquivos 'digital': {len(digital_files)}")
    for name, size, source, desc in digital_files:
        print(f"    {name} ({size} bytes, {source}) → '{desc}'")

    # Teste 5: Performance e duplicatas
    print("\n🔍 TESTE 5: DUPLICATAS E PERFORMANCE")
    print("-" * 50)

    cursor.execute("SELECT COUNT(*) FROM files")
    total_files = cursor.fetchone()[0]
    print(f"  Total de arquivos: {total_files}")

    cursor.execute("""
        SELECT name, COUNT(*) as count 
        FROM files 
        GROUP BY LOWER(name) 
        HAVING COUNT(*) > 1 
        ORDER BY count DESC 
        LIMIT 5
    """)
    duplicates = cursor.fetchall()
    print(f"  Arquivos duplicados por nome: {len(duplicates)}")
    for name, count in duplicates:
        print(f"    {name}: {count} ocorrências")

    # Por tamanho
    cursor.execute("""
        SELECT 
            CASE 
                WHEN size < 1024*1024 THEN 'Pequeno (<1MB)'
                WHEN size < 10*1024*1024 THEN 'Médio (1-10MB)'
                WHEN size < 100*1024*1024 THEN 'Grande (10-100MB)'
                ELSE 'Muito Grande (>100MB)'
            END as size_category,
            COUNT(*) as count
        FROM files 
        GROUP BY size_category
    """)
    sizes = cursor.fetchall()
    print("\n  Distribuição por tamanho:")
    for category, count in sizes:
        print(f"    {category}: {count} arquivos")

    conn.close()

    # Teste 6: Análise de código
    print("\n🔍 TESTE 6: ANÁLISE DE CÓDIGO")
    print("-" * 50)

    code_files = [
        'src/ui.py', 'src/database.py', 'src/workers.py',
        'src/utils.py', 'src/widgets.py', 'app.py'
    ]

    total_lines = 0
    functions_found = []
    imports_found = []

    for file_path in code_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                total_lines += len(lines)

                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    # Procurar definições de função
                    if line.startswith('def ') and not line.startswith('def _'):
                        func_name = line.split('(')[0].replace('def ', '')
                        functions_found.append(
                            (func_name, file_path, line_num))

                    # Procurar imports
                    if line.startswith('import ') or line.startswith('from '):
                        imports_found.append(line)

    print(f"  Total de linhas de código: {total_lines}")
    print(f"  Funções públicas encontradas: {len(functions_found)}")

    # Mostrar algumas funções
    if functions_found:
        print("  Algumas funções públicas:")
        for func, file, line in functions_found[:10]:
            print(f"    {func}() em {file}:{line}")

    # Contar imports únicos
    unique_imports = set(imports_found)
    print(f"  Imports únicos: {len(unique_imports)}")

    # Procurar possíveis problemas
    print("\n⚠️  POSSÍVEIS PROBLEMAS ENCONTRADOS:")

    # Imports duplicados
    import_count = {}
    for imp in imports_found:
        import_count[imp] = import_count.get(imp, 0) + 1

    duplicated_imports = [(imp, count)
                          for imp, count in import_count.items() if count > 1]
    if duplicated_imports:
        print("  Imports duplicados:")
        for imp, count in duplicated_imports[:5]:
            print(f"    '{imp}': {count} vezes")
    else:
        print("  ✅ Nenhum import duplicado encontrado")

    # Funções com nomes similares
    func_names = [f[0].lower() for f in functions_found]
    similar_funcs = []
    for i, name1 in enumerate(func_names):
        for j, name2 in enumerate(func_names[i+1:], i+1):
            if len(name1) > 3 and len(name2) > 3:
                # Verificar similaridade simples
                if name1 in name2 or name2 in name1:
                    similar_funcs.append(
                        (functions_found[i][0], functions_found[j][0]))

    if similar_funcs:
        print("  Funções com nomes similares:")
        for f1, f2 in similar_funcs[:5]:
            print(f"    {f1} ↔ {f2}")
    else:
        print("  ✅ Nenhuma função com nome similar encontrada")

    print("\n" + "="*70)
    print("🎉 TESTE COMPLETO FINALIZADO!")
    print("="*70)


if __name__ == "__main__":
    try:
        run_all_tests()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
