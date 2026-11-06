import sqlite3
import json

conn = sqlite3.connect('propval.db')
cur = conn.cursor()

print("--- DATASETS ---")
cur.execute("SELECT id, name, source_type, license_type, total_rows, valid_rows, status, approval_status, is_usable_for_ml FROM datasets")
datasets = cur.fetchall()
for d in datasets:
    print(f"Dataset {d[0][:8]}: name='{d[1]}', src_type='{d[2]}', lic_type='{d[3]}', total={d[4]}, valid={d[5]}, status='{d[6]}', approval='{d[7]}', ml_usable={d[8]}")

print("\n--- IMPORTED TRANSACTIONS BREAKDOWN ---")
cur.execute("SELECT is_verified_deed, is_asking_price, data_source, count(*) FROM imported_transactions GROUP BY is_verified_deed, is_asking_price, data_source")
for row in cur.fetchall():
    print(f"  verified={row[0]}, asking={row[1]}, source='{row[2]}', count={row[3]}")

print("\n--- VERIFICATION EVIDENCE BREAKDOWN ---")
cur.execute("SELECT verification_status, verifier_method, count(*) FROM verification_evidence GROUP BY verification_status, verifier_method")
for row in cur.fetchall():
    print(f"  status='{row[0]}', method='{row[1]}', count={row[2]}")

print("\n--- QUARANTINED RECORDS BREAKDOWN ---")
cur.execute("SELECT quarantine_code, resolution_status, count(*) FROM quarantined_records GROUP BY quarantine_code, resolution_status")
for row in cur.fetchall():
    print(f"  code='{row[0]}', resolution='{row[1]}', count={row[2]}")

print("\n--- REJECTED RECORDS BREAKDOWN ---")
cur.execute("SELECT rejection_code, count(*) FROM rejected_records GROUP BY rejection_code")
for row in cur.fetchall():
    print(f"  code='{row[0]}', count={row[1]}")

print("\n--- DUPLICATE RECORDS BREAKDOWN ---")
cur.execute("SELECT count(*) FROM duplicate_records")
print(f"  total_duplicates: {cur.fetchone()[0]}")

print("\n--- RAW TRANSACTION STAGING BREAKDOWN ---")
cur.execute("SELECT pii_scrub_status, count(*) FROM raw_transaction_staging GROUP BY pii_scrub_status")
for row in cur.fetchall():
    print(f"  pii_status='{row[0]}', count={row[1]}")

print("\n--- INGESTION JOBS BREAKDOWN ---")
cur.execute("SELECT status, count(*) FROM ingestion_jobs GROUP BY status")
for row in cur.fetchall():
    print(f"  job_status='{row[0]}', count={row[1]}")

conn.close()

