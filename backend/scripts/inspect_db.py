import sqlite3
import os

for path in ['propval.db', 'backend/propval.db']:
    if os.path.exists(path):
        print(f"=== {path} (size: {os.path.getsize(path)} bytes) ===")
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;").fetchall()
        for t in tables:
            name = t[0]
            cnt = cur.execute(f"SELECT COUNT(*) FROM {name};").fetchone()[0]
            print(f"  {name}: {cnt} rows")
        conn.close()
