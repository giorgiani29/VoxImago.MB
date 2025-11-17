"""
Utilitário para atualizar letra do drive nos caminhos do banco de dados
Útil quando a letra do drive mapeado muda (ex: G: -> L:)
"""

import sqlite3
import sys
import os

DB_PATH = 'data/file_index.db'
OLD_LETTER = 'G:/'
NEW_LETTER = 'L:/'


def update_drive_letter():
    try:
        if not os.path.exists(DB_PATH):
            print(f"❌ Arquivo de banco de dados não encontrado: {DB_PATH}")
            return False

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        count_sql = "SELECT COUNT(*) FROM files WHERE path LIKE ?;"
        cursor.execute(count_sql, (OLD_LETTER + '%',))
        count_before = cursor.fetchone()[0]

        if count_before == 0:
            print(f"ℹ️ Nenhum caminho encontrado com a letra {OLD_LETTER}")
            return True

        print(
            f"📊 Serão atualizados {count_before} caminhos de {OLD_LETTER} para {NEW_LETTER}")

        update_sql = """
        UPDATE files
        SET path = REPLACE(path, ?, ?)
        WHERE path LIKE ?;
        """

        cursor.execute(update_sql, (OLD_LETTER, NEW_LETTER, OLD_LETTER + '%'))

        affected_rows = cursor.rowcount
        conn.commit()

        print(f"✅ Letra do drive alterada: {OLD_LETTER} → {NEW_LETTER}")
        print(f"📊 {affected_rows} caminhos atualizados com sucesso")

        return True

    except sqlite3.Error as e:
        print(f"❌ Erro de banco de dados: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False
    finally:
        try:
            if 'conn' in locals():
                conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao fechar conexão: {e}")


if __name__ == "__main__":
    try:
        success = update_drive_letter()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)
