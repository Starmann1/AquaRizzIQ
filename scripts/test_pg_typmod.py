import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='root', dbname='aquarizz')
cur = conn.cursor()
cur.execute("SELECT proname FROM pg_proc WHERE proname LIKE '%typmod%'")
rows = cur.fetchall()
print('Typmod functions in PG:', [r[0] for r in rows])

# Can we create a shell type and define typmod in C? C libraries require DLL in lib.
conn.close()
