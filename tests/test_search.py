import sqlite3
conn = sqlite3.connect('file_index.db')
cursor = conn.cursor()
term = 'teste'
query = f'SELECT name, description FROM search_index WHERE search_index MATCH "{term}" LIMIT 5'
cursor.execute(query)
results = cursor.fetchall()
print(f'Resultados para {term}: {len(results)}')
for r in results:
    print(f'Nome: {r[0]}, Desc: {r[1]}')
conn.close()
