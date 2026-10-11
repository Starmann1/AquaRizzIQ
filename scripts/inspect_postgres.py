import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='root', dbname='aquarizz')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = cur.fetchall()
print(f"Total PostgreSQL Tables: {len(tables)}")
for t in sorted(tables):
    cur.execute(f'SELECT count(*) FROM "{t[0]}"')
    cnt = cur.fetchone()[0]
    print(f"  {t[0]}: {cnt} rows")
conn.close()
