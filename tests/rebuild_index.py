# Este código recria um índice de busca em um banco de dados SQLite.
# Ele usa a extensão FTS5 para criar um índice virtual com suporte a buscas rápidas.
# Os dados são processados e inseridos no índice, permitindo buscas eficientes.

import sqlite3

conn = sqlite3.connect('file_index.db')
cursor = conn.cursor()

cursor.execute('DROP TABLE IF EXISTS search_index')

cursor.execute('''
    CREATE VIRTUAL TABLE search_index USING fts5(
        name,
        description,
        file_id UNINDEXED,
        source UNINDEXED,
        tokenize='trigram'
    )
''')

cursor.execute('SELECT name, description, file_id, source FROM files')
rows = cursor.fetchall()
data = [(row[0].lower() if row[0] else '', row[1].lower()
         if row[1] else '', row[2], row[3]) for row in rows]
cursor.executemany('INSERT INTO search_index VALUES (?, ?, ?, ?)', data)

conn.commit()
conn.close()
print('Índice rebuild com trigram')
