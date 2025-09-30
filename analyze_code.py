#!/usr/bin/env python3
"""Análise detalhada de funções não utilizadas e código duplicado"""

import ast
import os
import re


def analyze_unused_functions():
    print("🔍 ANÁLISE DE FUNÇÕES NÃO UTILIZADAS")
    print("=" * 60)

    functions_defined = {}
    functions_called = set()

    python_files = [
        'src/ui.py', 'src/database.py', 'src/workers.py',
        'src/utils.py', 'src/widgets.py', 'src/file_list_model.py',
        'src/file_list_delegate.py', 'app.py'
    ]

    for file_path in python_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

                func_defs = re.findall(
                    r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', content)
                for func_name in func_defs:
                    functions_defined[func_name] = file_path
                func_calls = re.findall(
                    r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', content)
                functions_called.update(func_calls)

    print(f"📊 Funções definidas: {len(functions_defined)}")
    print(f"📊 Funções chamadas: {len(functions_called)}")

    # 2. Identificar funções possivelmente não utilizadas
    unused = []
    for func_name, file_path in functions_defined.items():
        # Ignorar métodos especiais, privados e main
        if (not func_name.startswith('_') and
            func_name != 'main' and
                func_name not in functions_called):
            unused.append((func_name, file_path))

    print(f"\n⚠️ FUNÇÕES POSSIVELMENTE NÃO UTILIZADAS ({len(unused)}):")
    for func_name, file_path in sorted(unused):
        print(f"  • {func_name}() em {file_path}")

    return unused


def analyze_duplicate_code():
    print("\n🔍 ANÁLISE DE CÓDIGO DUPLICADO")
    print("=" * 60)

    python_files = [
        'src/ui.py', 'src/database.py', 'src/workers.py',
        'src/utils.py', 'src/widgets.py', 'src/file_list_model.py',
        'src/file_list_delegate.py', 'app.py'
    ]

    # 1. Análise de imports duplicados
    all_imports = []
    import_by_file = {}

    for file_path in python_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                file_imports = []

                for line in lines:
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        all_imports.append(line)
                        file_imports.append(line)

                import_by_file[file_path] = file_imports

    # Contar frequência de imports
    import_count = {}
    for imp in all_imports:
        import_count[imp] = import_count.get(imp, 0) + 1

    duplicated_imports = [(imp, count)
                          for imp, count in import_count.items() if count > 2]
    duplicated_imports.sort(key=lambda x: x[1], reverse=True)

    print(f"\n📦 IMPORTS DUPLICADOS (usados 3+ vezes):")
    for imp, count in duplicated_imports[:10]:
        print(f"  • '{imp}': {count} vezes")
        # Mostrar em quais arquivos
        files_using = [f for f, imports in import_by_file.items()
                       if imp in imports]
        print(
            f"    Usado em: {', '.join([os.path.basename(f) for f in files_using])}")

    # 2. Análise de funções similares
    print(f"\n🔄 FUNÇÕES COM NOMES SIMILARES:")
    functions_defined = {}

    for file_path in python_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                func_defs = re.findall(
                    r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', content)
                for func_name in func_defs:
                    if func_name in functions_defined:
                        functions_defined[func_name].append(file_path)
                    else:
                        functions_defined[func_name] = [file_path]

    # Procurar funções com mesmo nome em arquivos diferentes
    duplicate_functions = {name: files for name,
                           files in functions_defined.items() if len(files) > 1}

    if duplicate_functions:
        for func_name, files in duplicate_functions.items():
            print(f"  • {func_name}(): definida em {len(files)} arquivos")
            for file_path in files:
                print(f"    - {file_path}")
    else:
        print("  ✅ Nenhuma função duplicada encontrada")

    # 3. Procurar padrões similares de código
    print(f"\n🔍 PADRÕES DE CÓDIGO SIMILARES:")

    # Procurar blocos try-except similares
    try_except_patterns = []
    for file_path in python_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Encontrar blocos try-except
                try_blocks = re.findall(
                    r'try:\s*\n(.*?)\nexcept.*?:', content, re.DOTALL)
                for block in try_blocks:
                    # Simplificar o bloco para comparação
                    simplified = re.sub(r'\s+', ' ', block.strip())
                    if len(simplified) > 20:  # Ignorar blocos muito pequenos
                        try_except_patterns.append((simplified, file_path))

    # Contar padrões similares
    pattern_count = {}
    for pattern, file_path in try_except_patterns:
        if pattern in pattern_count:
            pattern_count[pattern].append(file_path)
        else:
            pattern_count[pattern] = [file_path]

    similar_patterns = {p: files for p,
                        files in pattern_count.items() if len(files) > 1}

    if similar_patterns:
        print(
            f"  Encontrados {len(similar_patterns)} padrões try-except similares:")
        for i, (pattern, files) in enumerate(list(similar_patterns.items())[:3], 1):
            print(f"    {i}. Padrão usado em {len(files)} arquivos")
            print(f"       Código: {pattern[:60]}...")
            print(
                f"       Arquivos: {', '.join([os.path.basename(f) for f in files])}")
    else:
        print("  ✅ Nenhum padrão duplicado encontrado")


def analyze_file_sizes():
    print(f"\n📊 ANÁLISE DE TAMANHOS DE ARQUIVO")
    print("=" * 60)

    python_files = [
        'src/ui.py', 'src/database.py', 'src/workers.py',
        'src/utils.py', 'src/widgets.py', 'src/file_list_model.py',
        'src/file_list_delegate.py', 'app.py'
    ]

    file_stats = []
    total_lines = 0

    for file_path in python_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                line_count = len(lines)
                total_lines += line_count

                # Contar linhas de código (não comentários/vazias)
                code_lines = 0
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#'):
                        code_lines += 1

                file_size = os.path.getsize(file_path)
                file_stats.append(
                    (file_path, line_count, code_lines, file_size))

    # Ordenar por número de linhas
    file_stats.sort(key=lambda x: x[1], reverse=True)

    print(f"📈 Total de linhas: {total_lines}")
    print(f"📁 Arquivo maior → menor:")

    for file_path, total_lines, code_lines, size_bytes in file_stats:
        percentage = (code_lines / total_lines * 100) if total_lines > 0 else 0
        size_kb = size_bytes / 1024
        print(f"  • {os.path.basename(file_path):<25} {total_lines:>4} linhas ({code_lines:>3} código - {percentage:>2.0f}%) {size_kb:>6.1f}KB")

    # Identificar arquivos que podem precisar de refatoração
    large_files = [f for f in file_stats if f[1] > 500]  # Mais de 500 linhas
    if large_files:
        print(f"\n⚠️  ARQUIVOS GRANDES (>500 linhas) - Considere refatorar:")
        for file_path, total_lines, code_lines, size_bytes in large_files:
            print(f"  • {os.path.basename(file_path)}: {total_lines} linhas")


if __name__ == "__main__":
    try:
        unused = analyze_unused_functions()
        analyze_duplicate_code()
        analyze_file_sizes()

        print(f"\n" + "="*60)
        print(f"📋 RESUMO DA ANÁLISE")
        print(f"="*60)
        print(f"• Funções não utilizadas encontradas: {len(unused)}")
        print(f"• Recomendação: Revisar as funções listadas")
        print(f"• Código duplicado: Verificar imports e padrões")
        print(f"• Estrutura geral: Boa organização em módulos")
        print(f"="*60)

    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
