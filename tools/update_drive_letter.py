import sqlite3

DB_PATH = 'data/file_index.db'
OLD_LETTER = 'G:/'
NEW_LETTER = 'L:/'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

update_sql = """
UPDATE files
SET path = REPLACE(path, ?, ?)
WHERE path LIKE ?;
"""
cursor.execute(update_sql, (OLD_LETTER, NEW_LETTER, OLD_LETTER + '%'))

conn.commit()
print(
    f"Letra do drive alterada de {OLD_LETTER} para {NEW_LETTER} nos caminhos da tabela 'files'.")

conn.close()
