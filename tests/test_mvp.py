#!/usr/bin/env python3
"""
Script de teste para validar o MVP do VoxImago
Verifica se todas as funcionalidades básicas estão funcionando
"""

import sys
import os
import sqlite3
from pathlib import Path


def test_database_connection():
    try:
        conn = sqlite3.connect('file_index.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()

        required_tables = ['files', 'search_index']
        existing_tables = [table[0] for table in tables]

        for table in required_tables:
            if table not in existing_tables:
                print(f"❌ Tabela {table} não encontrada")
                return False

        print("✅ Banco de dados SQLite conectado com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao conectar com banco: {e}")
        return False


def test_credentials():
    if os.path.exists('credentials.json'):
        print("✅ Arquivo credentials.json encontrado")
        return True
    else:
        print("❌ Arquivo credentials.json não encontrado")
        return False


def test_dependencies():
    required_modules = [
        'PyQt6',
        'google.auth',
        'googleapiclient',
        'requests',
        'cv2'
    ]

    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} instalado")
        except ImportError:
            print(f"❌ {module} não encontrado")
            missing.append(module)

    return len(missing) == 0


def test_file_structure():
    required_files = [
        'app.py',
        'ui.py',
        'database.py',
        'workers.py',
        'utils.py',
        'widgets.py',
        'file_list_model.py',
        'file_list_delegate.py',
        'requirements.txt'
    ]

    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} encontrado")
        else:
            print(f"❌ {file} não encontrado")
            missing.append(file)

    return len(missing) == 0


def test_directories():
    required_dirs = ['icons', 'thumbnail_cache']

    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name)
                print(f"✅ Diretório {dir_name} criado")
            except Exception as e:
                print(f"❌ Erro ao criar diretório {dir_name}: {e}")
                return False
        else:
            print(f"✅ Diretório {dir_name} existe")

    return True


def main():
    print("🚀 Executando testes do MVP VoxImago...")
    print("=" * 50)

    tests = [
        ("Estrutura de arquivos", test_file_structure),
        ("Diretórios", test_directories),
        ("Dependências Python", test_dependencies),
        ("Credenciais Google", test_credentials),
        ("Banco de dados", test_database_connection)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Testando: {test_name}")
        result = test_func()
        results.append((test_name, result))
        print("-" * 30)

    print("\n📊 RESUMO DOS TESTES:")
    print("=" * 50)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Seu MVP está pronto para uso!")
        print("\n📋 Para usar o aplicativo:")
        print("1. Execute: python app.py")
        print("2. Faça login no Google Drive (se necessário)")
        print("3. Configure as pastas locais em 'Ferramentas > Pastas Locais'")
        print("4. Use a busca para encontrar arquivos")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM")
        print("❗ Corrija os problemas antes de usar o MVP")

        # Sugestões de correção
        print("\n🔧 SUGESTÕES DE CORREÇÃO:")
        for test_name, passed in results:
            if not passed:
                if "Dependências" in test_name:
                    print("   → Execute: pip install -r requirements.txt")
                elif "Credenciais" in test_name:
                    print("   → Obtenha credentials.json do Google Cloud Console")
                elif "Banco" in test_name:
                    print("   → Execute o aplicativo uma vez para criar o banco")


if __name__ == "__main__":
    main()
