import sqlite3
import json

conn = sqlite3.connect('propval.db')
c = conn.cursor()

print("==================================================")
print("PROPVAL AI - PHASE 6B DATASET & QUALITY AUDIT")
print("==================================================")

print("\n--- 1. TABLE ROW COUNTS ---")
for t in ['raw_transaction_staging', 'imported_transactions', 'duplicate_records', 'rejected_records', 'quarantined_records', 'verification_evidence', 'datasets', 'dataset_versions']:
    cnt = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {cnt}")

print("\n--- 2. LIFECYCLE BREAKDOWN ---")
raw_cnt = c.execute("SELECT COUNT(*) FROM raw_transaction_staging").fetchone()[0]
scrubbed_cnt = c.execute("SELECT COUNT(*) FROM raw_transaction_staging WHERE pii_scrub_status = 'SCRUBBED'").fetchone()[0]
normalized_cnt = c.execute("SELECT COUNT(*) FROM imported_transactions").fetchone()[0]
pending_quarantine = c.execute("SELECT COUNT(*) FROM quarantined_records WHERE resolution_status = 'PENDING_REVIEW'").fetchone()[0]
verified_cnt = c.execute("SELECT COUNT(*) FROM imported_transactions WHERE is_verified_deed = 1").fetchone()[0]
rejected_cnt = c.execute("SELECT COUNT(*) FROM rejected_records").fetchone()[0]
quarantined_cnt = c.execute("SELECT COUNT(*) FROM quarantined_records").fetchone()[0]
duplicate_cnt = c.execute("SELECT COUNT(*) FROM duplicate_records").fetchone()[0]

print(f"  RAW Staged: {raw_cnt}")
print(f"  PARSED & PII Scrubbed: {scrubbed_cnt}")
print(f"  NORMALIZED: {normalized_cnt}")
print(f"  VALIDATION_PENDING (Quarantine Pending): {pending_quarantine}")
print(f"  VALIDATED: {normalized_cnt}")
print(f"  VERIFIED (is_verified_deed = 1): {verified_cnt}")
print(f"  REJECTED: {rejected_cnt}")
print(f"  QUARANTINED (Total): {quarantined_cnt}")
print(f"  DUPLICATES: {duplicate_cnt}")

print("\n--- 3. DATASET VERSIONS & CERTIFIED DEEDS ---")
versions = c.execute("SELECT id, semver_tag, version_title, total_records, verified_records, approval_status, is_ml_eligible, dataset_checksum_sha256 FROM dataset_versions").fetchall()
for v in versions:
    print(f"  Version: {v[1]} ({v[2]}) | Status: {v[5]} | ML Eligible: {v[6]} | Total: {v[3]} | Verified: {v[4]} | Hash: {v[7][:12]}...")

print("\n--- 4. CERTIFIED DEED UNIQUE COUNT IN APPROVED DATASETS ---")
# Check how many distinct transaction IDs are included in approved dataset_versions
approved_versions = c.execute("SELECT id, semver_tag, included_transaction_ids FROM dataset_versions WHERE approval_status = 'APPROVED'").fetchall()
approved_tx_ids = set()
for av in approved_versions:
    try:
        tx_ids = json.loads(av[2])
        approved_tx_ids.update(tx_ids)
    except Exception as e:
        pass
print(f"  Unique Transaction IDs across all APPROVED Dataset Versions: {len(approved_tx_ids)}")

# Filter those transaction IDs in imported_transactions that have is_verified_deed = 1
if approved_tx_ids:
    placeholders = ",".join("?" * len(approved_tx_ids))
    cert_count = c.execute(f"SELECT COUNT(*) FROM imported_transactions WHERE id IN ({placeholders}) AND is_verified_deed = 1", list(approved_tx_ids)).fetchone()[0]
    print(f"  Certified Empirical Deeds (is_verified_deed=1 in approved datasets): {cert_count}")
else:
    cert_count = 0
    print(f"  Certified Empirical Deeds: 0")

print("\n--- 5. SOURCE DISTRIBUTION (imported_transactions) ---")
sources = c.execute("SELECT data_source, COUNT(*), SUM(is_verified_deed) FROM imported_transactions GROUP BY data_source").fetchall()
for s in sources:
    print(f"  Source: {s[0]} | Total: {s[1]} | Verified: {s[2]}")

print("\n--- 6. GEOGRAPHIC DISTRIBUTION (imported_transactions) ---")
geos = c.execute("SELECT city, locality, COUNT(*), SUM(is_verified_deed) FROM imported_transactions GROUP BY city, locality").fetchall()
for g in geos:
    print(f"  City: {g[0]} | Locality: {g[1]} | Total: {g[2]} | Verified: {g[3]}")

print("\n--- 7. PROPERTY TYPE DISTRIBUTION ---")
ptypes = c.execute("SELECT property_type, COUNT(*), SUM(is_verified_deed) FROM imported_transactions GROUP BY property_type").fetchall()
for pt in ptypes:
    print(f"  Type: {pt[0]} | Total: {pt[1]} | Verified: {pt[2]}")

print("\n--- 8. TRANSACTION DATE DISTRIBUTION ---")
dates = c.execute("SELECT substr(transaction_date, 1, 4) as yr, COUNT(*), SUM(is_verified_deed) FROM imported_transactions GROUP BY yr ORDER BY yr").fetchall()
for d in dates:
    print(f"  Year: {d[0]} | Total: {d[1]} | Verified: {d[2]}")

print("\n--- 9. MISSING VALUE ANALYSIS ---")
cols_to_check = [
    'carpet_area_sqft', 'built_up_area_sqft', 'super_built_up_area_sqft',
    'floor_no', 'total_floors', 'age_years', 'transaction_price',
    'price_per_sqft', 'guideline_rate_per_sqft', 'deviation_from_guideline_pct',
    'latitude', 'longitude', 'survey_number', 'village_name', 'taluka_tehsil', 'sro_jurisdiction_code'
]
total_imported = c.execute("SELECT COUNT(*) FROM imported_transactions").fetchone()[0]
total_verified = c.execute("SELECT COUNT(*) FROM imported_transactions WHERE is_verified_deed = 1").fetchone()[0]

print(f"  Total imported: {total_imported}, Total verified: {total_verified}")
for col in cols_to_check:
    null_all = c.execute(f"SELECT COUNT(*) FROM imported_transactions WHERE {col} IS NULL OR {col} = ''").fetchone()[0]
    null_ver = c.execute(f"SELECT COUNT(*) FROM imported_transactions WHERE is_verified_deed = 1 AND ({col} IS NULL OR {col} = '')").fetchone()[0]
    pct_all = (null_all / total_imported) * 100 if total_imported > 0 else 0
    pct_ver = (null_ver / total_verified) * 100 if total_verified > 0 else 0
    print(f"  Column {col:30} | All Null: {null_all} ({pct_all:5.1f}%) | Verified Null: {null_ver} ({pct_ver:5.1f}%)")

print("\n--- 10. QUARANTINE BREAKDOWN ---")
quarantine = c.execute("SELECT quarantine_code, quarantine_reason, resolution_status, COUNT(*) FROM quarantined_records GROUP BY quarantine_code, quarantine_reason, resolution_status").fetchall()
for q in quarantine:
    print(f"  Code: {q[0]} | Reason: {q[1]} | Status: {q[2]} | Count: {q[3]}")

print("\n--- 11. REJECTED BREAKDOWN ---")
rej = c.execute("SELECT rejection_code, rejection_reason, COUNT(*) FROM rejected_records GROUP BY rejection_code, rejection_reason").fetchall()
for r in rej:
    print(f"  Code: {r[0]} | Reason: {r[1]} | Count: {r[2]}")

print("\n--- 12. DUPLICATE FINGERPRINTS ---")
dup_stats = c.execute("SELECT COUNT(*), COUNT(DISTINCT fingerprint_hash) FROM duplicate_records").fetchone()
print(f"  Total Duplicates in table: {dup_stats[0]} | Distinct Fingerprints: {dup_stats[1]}")

print("\n==================================================")
