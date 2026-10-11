import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def setup_db():
    print("Connecting to postgres database...")
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='root', dbname='postgres')
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname='aquarizz'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE aquarizz")
        print("Created database 'aquarizz'")
    else:
        print("Database 'aquarizz' already exists")
    conn.close()

    print("Connecting to aquarizz database...")
    conn_aqua = psycopg2.connect(host='localhost', port=5432, user='postgres', password='root', dbname='aquarizz')
    conn_aqua.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur_aqua = conn_aqua.cursor()

    try:
        cur_aqua.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cur_aqua.execute("SELECT PostGIS_Version();")
        ver = cur_aqua.fetchone()
        print("PostGIS extension enabled successfully! Version:", ver[0])
    except Exception as e:
        print("PostGIS warning/error:", e)

    conn_aqua.close()

if __name__ == "__main__":
    setup_db()
