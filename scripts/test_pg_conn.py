import psycopg2

passwords = [
    'postgres', 'admin', 'root', 'password', '1234', '123456', '12345678',
    'aquarizz', 'chennai', 'pgadmin', '', 'garul', 'Garul', 'postgis'
]
users = ['postgres', 'garul']

success = False
for u in users:
    for p in passwords:
        try:
            conn = psycopg2.connect(host='localhost', port=5432, user=u, password=p, dbname='postgres', connect_timeout=1)
            print(f"SUCCESS with user='{u}', password='{p}'")
            conn.close()
            success = True
            break
        except Exception as e:
            pass
    if success:
        break

if not success:
    print("None of test passwords worked.")
