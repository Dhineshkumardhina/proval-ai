import sqlite3

for db_path in ['backend/propval.db', 'propval.db']:
    print(f"=== DATABASE: {db_path} ===")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print("Tables:", tables)
        for t in [
            'data_sources',
            'ingestion_jobs',
            'raw_transaction_staging',
            'datasets',
            'imported_transactions',
            'duplicate_records',
            'rejected_records',
            'quarantined_records',
            'verification_evidence',
            'dataset_versions'
        ]:
            if t in tables:
                cur.execute(f"SELECT count(*) FROM {t}")
                cnt = cur.fetchone()[0]
                print(f"  {t}: {cnt}")
        conn.close()
    except Exception as e:
        print(f"Error reading {db_path}: {e}")
