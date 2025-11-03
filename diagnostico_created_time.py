import sqlite3

db_path = "data/file_index.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Menores valores de createdTime:")
for row in cursor.execute("SELECT file_id, name, createdTime FROM files ORDER BY createdTime ASC LIMIT 20;"):
    print(row)

print("\nMaiores valores de createdTime:")
for row in cursor.execute("SELECT file_id, name, createdTime FROM files ORDER BY createdTime DESC LIMIT 20;"):
    print(row)

print("\nValores suspeitos (muito grandes, muito pequenos ou não inteiros):")
for row in cursor.execute("SELECT file_id, name, createdTime FROM files WHERE typeof(createdTime) != 'integer' OR createdTime > 9999999999 OR createdTime < 1000000000 LIMIT 20;"):
    print(row)

conn.close()
