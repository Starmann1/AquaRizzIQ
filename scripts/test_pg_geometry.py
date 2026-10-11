import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='root', dbname='aquarizz')
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

try:
    cur.execute("CREATE DOMAIN geometry AS bytea;")
    print("Created DOMAIN geometry AS bytea")
except Exception as e:
    print("Domain geometry error:", e)

# Test if a table with geometry column can be created
try:
    cur.execute("CREATE TABLE IF NOT EXISTS test_geom (id int, geom geometry);")
    print("Table test_geom created successfully!")
    cur.execute("DROP TABLE test_geom;")
except Exception as e:
    print("Table creation error:", e)

conn.close()
