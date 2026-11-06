import sqlite3
import json

conn = sqlite3.connect('propval.db')
cur = conn.cursor()

# 1. RAW records
cur.execute("SELECT count(*) FROM raw_transaction_staging")
raw_count = cur.fetchone()[0]

# 2. PARSED / CLEANSED
cur.execute("SELECT count(*) FROM raw_transaction_staging WHERE pii_scrub_status = 'CLEANSED'")
parsed_count = cur.fetchone()[0]

# 3. NORMALIZED (Imported transactions total)
cur.execute("SELECT count(*) FROM imported_transactions")
normalized_count = cur.fetchone()[0]

# 4. VALIDATION_PENDING (Quarantined pending review)
cur.execute("SELECT count(*) FROM quarantined_records WHERE resolution_status = 'PENDING_REVIEW'")
validation_pending_count = cur.fetchone()[0]

# 5. VALIDATED (Passed normalization and not rejected)
cur.execute("SELECT count(*) FROM imported_transactions WHERE is_asking_price = 0")
validated_count = cur.fetchone()[0]

# 6. VERIFIED (is_verified_deed = 1 in imported_transactions)
cur.execute("SELECT count(*) FROM imported_transactions WHERE is_verified_deed = 1")
verified_count = cur.fetchone()[0]

# 7. CERTIFIED (Verified deeds in approved datasets with commercial provenance)
cur.execute("""
    SELECT count(DISTINCT it.fingerprint_hash) 
    FROM imported_transactions it
    JOIN datasets d ON it.dataset_id = d.id
    WHERE it.is_verified_deed = 1
      AND d.approval_status = 'APPROVED'
      AND d.source_type = 'commercial_license'
""")
certified_count = cur.fetchone()[0]

# 8. REJECTED
cur.execute("SELECT count(*) FROM rejected_records")
rejected_count = cur.fetchone()[0]

# 9. QUARANTINED
cur.execute("SELECT count(*) FROM quarantined_records")
quarantined_count = cur.fetchone()[0]

# 10. DUPLICATES
cur.execute("SELECT count(*) FROM duplicate_records")
duplicate_count = cur.fetchone()[0]

print("=== LIFECYCLE STATE COUNTS ===")
print(f"RAW:                {raw_count}")
print(f"PARSED:             {parsed_count}")
print(f"NORMALIZED:         {normalized_count}")
print(f"VALIDATION_PENDING: {validation_pending_count}")
print(f"VALIDATED:          {validated_count}")
print(f"VERIFIED:           {verified_count}")
print(f"CERTIFIED:          {certified_count}")
print(f"REJECTED:           {rejected_count}")
print(f"QUARANTINED:        {quarantined_count}")
print(f"DUPLICATE_RECORDS:  {duplicate_count}")

# Check verified deeds in detail
print("\n=== VERIFIED DEEDS BY DATASET AND SOURCE ===")
cur.execute("""
    SELECT d.id, d.name, d.source_type, d.approval_status, it.data_source, count(it.id)
    FROM imported_transactions it
    JOIN datasets d ON it.dataset_id = d.id
    WHERE it.is_verified_deed = 1
    GROUP BY d.id, it.data_source
""")
for r in cur.fetchall():
    print(f"Dataset {r[0][:8]} ({r[1]} | {r[2]} | {r[3]}): source='{r[4]}', count={r[5]}")

conn.close()

