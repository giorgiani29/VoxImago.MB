"""
Script de verificação de datas - Encontra arquivos com datas inválidas no banco
Testa: datas NULL, zero ou malformadas nas colunas created_time e modified_time
"""

import sqlite3
import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PATH = "data/file_index.db"


def check_invalid_dates():

    if not os.path.exists(DB_PATH):
        print(f"❌ Erro: Banco de dados não encontrado em '{DB_PATH}'.")
        print("Execute a aplicação ao menos uma vez para criar o banco.")
        return

    print(f"🔍 Conectando ao banco de dados em '{DB_PATH}'...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT path, name, createdTime, modifiedTime, source
    FROM files
    WHERE createdTime IS NULL OR createdTime = 0 OR createdTime = '' OR
          modifiedTime IS NULL OR modifiedTime = 0 OR modifiedTime = '';
    """

    print("\nExecutando a seguinte query para encontrar datas inválidas:")
    print(query)

    try:
        cursor.execute(query)
        invalid_files = cursor.fetchall()

        if not invalid_files:
            print(
                "\n✅ Nenhum arquivo com data inválida (NULL, 0, ou vazia) foi encontrado.")
        else:
            print(
                f"\n🚨 Encontrados {len(invalid_files)} arquivos com datas inválidas:")
            print("-" * 80)
            print(
                f"{'Origem':<8} | {'Data de Criação':<25} | {'Data de Modificação':<25} | {'Caminho do Arquivo'}")
            print("-" * 80)

            for row in invalid_files:
                path, name, created, modified, source = row

                created_str = str(created) if created is not None else "NULL"
                modified_str = str(
                    modified) if modified is not None else "NULL"

                try:
                    if isinstance(created, (int, float)) and created > 0:
                        created_str = datetime.fromtimestamp(
                            created).strftime('%d/%m/%Y %H:%M:%S')
                except (ValueError, OSError):
                    pass

                try:
                    if isinstance(modified, (int, float)) and modified > 0:
                        modified_str = datetime.fromtimestamp(
                            modified).strftime('%d/%m/%Y %H:%M:%S')
                except (ValueError, OSError):
                    pass

                display_path = path if path else name
                print(
                    f"{source:<8} | {created_str:<25} | {modified_str:<25} | {display_path}")

            print("-" * 80)
            print("\n💡 Próximos passos:")
            print("1. Implementar um fallback no código de indexação para usar a data de modificação se a de criação falhar.")
            print(
                "2. Para arquivos já no banco, criar um script de correção para preencher as datas ausentes.")

    except sqlite3.Error as e:
        print(f"\n❌ Erro ao executar a query no banco de dados: {e}")
    finally:
        conn.close()
        print("\nConexão com o banco de dados fechada.")


if __name__ == "__main__":
    check_invalid_dates()
