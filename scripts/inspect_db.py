import sqlite3

conn = sqlite3.connect('aquarizz.db')
cur = conn.cursor()
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"Total tables: {len(tables)}")
for t in tables:
    try:
        count = cur.execute(f'SELECT count(*) FROM "{t[0]}"').fetchone()[0]
        print(f"  {t[0]}: {count} rows")
    except Exception as e:
        print(f"  {t[0]}: error {e}")
