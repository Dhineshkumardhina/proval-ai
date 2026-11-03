"""Empirical baseline benchmarking script for PropVal AI.

Measures:
- Backend API response times (single & batch)
- Database query counts (N+1 query profiling), EXPLAIN execution plans, connection pool latency
- ML inference latency (single, batch 10/50/100/500), model load time, memory consumption
"""

import json
import os
import sys
import time
import tracemalloc
import psutil
from datetime import datetime, timezone
import pandas as pd
import numpy as np

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import event
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, check_db_connectivity
from app.models.property import PropertyRecord
from app.models.valuation import ValuationCaseModel, ValuationResultModel
from app.models.dataset import DatasetMetadataModel, ImportedTransactionModel
from app.services import case_service, valuation_service, ingestion_service
from app.schemas.case import ValuationCaseCreate
from app.schemas.valuation import ValuationInputParams
from app.ml.model_service import ml_model_service
from app.ml.preprocessing import build_feature_vector
from app.ml.explainability import explain_catboost_prediction
from app.ml.benchmarks import evaluate_benchmarks
from catboost import CatBoostRegressor


def benchmark_database_queries():
    """Profile query count and execution plans to detect N+1 and slow queries."""
    db: Session = SessionLocal()
    
    # Ensure there are at least 15-20 cases in the DB to properly test list_cases
    existing_count = db.query(ValuationCaseModel).count()
    if existing_count < 15:
        print(f"Populating test cases (current count: {existing_count})...")
        for i in range(existing_count, 20):
            c_in = ValuationCaseCreate(
                borrowerName=f"Borrower {i}",
                city="Bengaluru" if i % 2 == 0 else "Mumbai",
                projectName=f"Prestige Heights {i}",
                unitAddress=f"Flat {i}01, Tower A",
                locality="Whitefield" if i % 2 == 0 else "Bandra West",
                propertyType="High-Rise Apartment",
                carpetAreaSqFt=1200.0 + (i * 25),
                superBuiltUpAreaSqFt=1550.0 + (i * 30),
                floorNo=(i % 15) + 1,
                totalFloors=20,
                ageYears=2,
                roadWidthFt=40.0,
                circleRatePerSqFt=8000.0 if i % 2 == 0 else 22000.0,
                baseMarketRatePerSqFt=10500.0 if i % 2 == 0 else 28000.0,
                loanRequested=7500000.0 + (i * 100000),
                declaredAgreementValue=9500000.0 + (i * 120000),
            )
            case_service.create_case(db, c_in)

    # Count SQL statements emitted by list_cases
    query_log = []
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        query_log.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)

    # 1. Benchmark list_cases(limit=20)
    query_log.clear()
    t0 = time.perf_counter()
    cases, total = case_service.list_cases(db, limit=20)
    db_list_latency_ms = (time.perf_counter() - t0) * 1000
    queries_for_list = len(query_log)

    # 2. Benchmark get_case_by_id
    query_log.clear()
    first_id = cases[0].id if cases else "dummy"
    t0 = time.perf_counter()
    c = case_service.get_case_by_id(db, first_id)
    db_get_latency_ms = (time.perf_counter() - t0) * 1000
    queries_for_get = len(query_log)

    event.remove(engine, "before_cursor_execute", before_cursor_execute)

    # 3. Connection latency probe
    conn_ok, conn_lat, dialect = check_db_connectivity(db)

    # 4. EXPLAIN QUERY PLAN
    explain_sql = "EXPLAIN QUERY PLAN SELECT * FROM valuation_cases JOIN properties ON valuation_cases.property_id = properties.id ORDER BY valuation_cases.created_at DESC LIMIT 20;"
    try:
        raw_conn = engine.raw_connection()
        cur = raw_conn.cursor()
        cur.execute(explain_sql)
        explain_plan = cur.fetchall()
        raw_conn.close()
    except Exception as e:
        explain_plan = [str(e)]

    db.close()

    return {
        "cases_returned": len(cases),
        "total_cases_in_db": total,
        "list_cases_latency_ms": round(db_list_latency_ms, 2),
        "queries_emitted_for_list_20": queries_for_list,
        "queries_emitted_for_get_1": queries_for_get,
        "connection_probe_latency_ms": conn_lat,
        "db_dialect": dialect,
        "explain_query_plan": explain_plan,
    }


def benchmark_ml_performance():
    """Benchmark CatBoost model training, model loading, and inference latencies."""
    tracemalloc.start()
    mem_before = psutil.Process().memory_info().rss / (1024 * 1024)

    # Create synthetic dataset for ML benchmark
    np.random.seed(42)
    n = 120
    df = pd.DataFrame({
        "carpet_area_sqft": np.random.uniform(800, 2500, n),
        "floor_no": np.random.randint(1, 20, n).astype(float),
        "total_floors": np.full(n, 20.0),
        "floor_ratio": np.random.uniform(0.05, 1.0, n),
        "guideline_rate_per_sqft": np.random.choice([6000.0, 8000.0, 10000.0], n),
        "age_years": np.random.uniform(0, 10, n),
        "city": ["Bengaluru"] * n,
        "locality": np.random.choice(["Whitefield", "Koramangala", "Indiranagar", "HSR Layout"], n),
        "property_type": ["High-Rise Apartment"] * n,
        "transaction_quarter": np.random.choice(["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"], n),
        "transaction_date": pd.date_range("2024-01-01", periods=n, freq="3D"),
    })
    df["transaction_price"] = (
        df["carpet_area_sqft"] * df["guideline_rate_per_sqft"] * 1.3
        + df["floor_no"] * 50000.0
        + np.random.normal(0, 50000, n)
    )

    train_df = df.iloc[:90].copy()
    test_df = df.iloc[90:].copy()

    # Model training time
    t0 = time.perf_counter()
    summary, cb_model = evaluate_benchmarks(train_df, test_df)
    train_time_ms = (time.perf_counter() - t0) * 1000

    # Save to temp artifact
    temp_artifact = "temp_benchmark_catboost.cbm"
    cb_model.save_model(temp_artifact)

    # Benchmark model loading time
    load_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        m = CatBoostRegressor()
        m.load_model(temp_artifact)
        load_times.append((time.perf_counter() - t0) * 1000)
    avg_load_time_ms = np.mean(load_times)

    # Benchmark single inference latency (with TreeSHAP explainability)
    sample_feat = build_feature_vector(
        city="Bengaluru",
        locality="Whitefield",
        property_type="High-Rise Apartment",
        carpet_area_sqft=1250.0,
        floor_no=7,
        total_floors=18,
        guideline_rate_per_sqft=7500.0,
        age_years=3,
        transaction_quarter="2024-Q3",
    )

    single_infer_times = []
    single_shap_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = cb_model.predict(sample_feat)[0]
        t1 = time.perf_counter()
        single_infer_times.append((t1 - t0) * 1000)

        t2 = time.perf_counter()
        explain_catboost_prediction(cb_model, sample_feat)
        single_shap_times.append((time.perf_counter() - t2) * 1000)

    # Benchmark batch inference latencies
    batch_results = {}
    for batch_size in [10, 50, 100, 500]:
        batch_feat = pd.concat([sample_feat] * batch_size, ignore_index=True)
        t0 = time.perf_counter()
        _ = cb_model.predict(batch_feat)
        dur_ms = (time.perf_counter() - t0) * 1000
        batch_results[f"batch_{batch_size}"] = {
            "total_latency_ms": round(dur_ms, 2),
            "per_record_latency_ms": round(dur_ms / batch_size, 3),
        }

    mem_after = psutil.Process().memory_info().rss / (1024 * 1024)
    traced_curr, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    if os.path.exists(temp_artifact):
        os.remove(temp_artifact)

    return {
        "training_time_ms": round(train_time_ms, 2),
        "model_loading_time_ms": round(float(avg_load_time_ms), 2),
        "single_inference_only_latency_ms": round(float(np.mean(single_infer_times)), 3),
        "single_inference_with_shap_latency_ms": round(float(np.mean(single_infer_times) + np.mean(single_shap_times)), 3),
        "single_tree_shap_latency_ms": round(float(np.mean(single_shap_times)), 3),
        "batch_inference": batch_results,
        "memory_rss_delta_mb": round(mem_after - mem_before, 2),
        "traced_peak_memory_mb": round(traced_peak / (1024 * 1024), 2),
    }


def benchmark_ingestion_performance():
    """Measure raw dataset parsing and ingestion throughput (rows/sec)."""
    db: Session = SessionLocal()
    
    # Generate CSV with 1,200 property deed records
    rows = []
    for i in range(1200):
        rows.append({
            "registration_date": f"2024-{(i%12)+1:02d}-15",
            "city": "Bengaluru" if i % 3 == 0 else "Mumbai" if i % 3 == 1 else "Delhi-NCR",
            "locality": f"Sector {i%20}",
            "project_name": f"Sobha City {i%10}",
            "carpet_area_sqft": 1000.0 + (i % 500),
            "unit": "sq ft",
            "transaction_price": 7500000 + (i * 10000),
            "property_type": "Apartment",
            "floor_no": (i % 15) + 1,
            "total_floors": 20,
            "pincode": "560001",
            "circle_rate": 7000.0,
            "latitude": 12.9716,
            "longitude": 77.5946,
        })
    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    meta = {
        "sourceType": "sro_registration",
        "description": "Benchmark Ingestion Test Dataset",
        "city": "Bengaluru",
        "subMarket": "East",
    }

    t0 = time.perf_counter()
    dataset, report = ingestion_service.ingest_dataset(
        db=db,
        file_bytes=csv_bytes,
        filename="benchmark_ingest_1200.csv",
        metadata=meta,
    )
    duration_sec = time.perf_counter() - t0
    rows_per_sec = 1200 / duration_sec

    # Cleanup test dataset records
    db.delete(report)
    db.query(ImportedTransactionModel).filter(ImportedTransactionModel.dataset_id == dataset.id).delete()
    db.delete(dataset)
    db.commit()
    db.close()

    return {
        "dataset_rows": 1200,
        "ingestion_duration_sec": round(duration_sec, 3),
        "ingestion_throughput_rows_per_sec": round(rows_per_sec, 1),
    }


def benchmark_valuation_calculation():
    """Benchmark raw mathematical valuation calculation throughput (pure computation)."""
    params = ValuationInputParams(
        carpetAreaSqFt=1200.0,
        superBuiltUpAreaSqFt=1560.0,
        baseMarketRatePerSqFt=12000.0,
        circleRatePerSqFt=9500.0,
        floorRiseFactor=350.0,
        roadWidthFactor=200.0,
        amenitiesPremium=400.0,
        structuralDepreciation=150.0,
        underwriterHaircutPct=10.0,
        distressDiscountPct=15.0,
        ltvRatioPct=75.0,
        legalRiskPenaltyPct=0.0,
    )

    t0 = time.perf_counter()
    iterations = 5000
    for _ in range(iterations):
        _ = valuation_service.calculate_valuation(params)
    dur_ms = (time.perf_counter() - t0) * 1000
    ops_per_sec = iterations / (dur_ms / 1000)

    return {
        "iterations": iterations,
        "total_duration_ms": round(dur_ms, 2),
        "latency_per_calc_microsec": round((dur_ms / iterations) * 1000, 2),
        "calculations_per_second": round(ops_per_sec, 1),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING PROPVAL AI BASELINE MEASUREMENTS")
    print("=" * 60)

    print("\n[1/4] Benchmarking Database Queries & Profiling N+1...")
    db_res = benchmark_database_queries()
    print(json.dumps(db_res, indent=2))

    print("\n[2/4] Benchmarking ML Engine & CatBoost Inference...")
    ml_res = benchmark_ml_performance()
    print(json.dumps(ml_res, indent=2))

    print("\n[3/4] Benchmarking Pure Valuation Calculation...")
    val_res = benchmark_valuation_calculation()
    print(json.dumps(val_res, indent=2))

    print("\n[4/4] Benchmarking Dataset Ingestion...")
    ingest_res = benchmark_ingestion_performance()
    print(json.dumps(ingest_res, indent=2))

    full_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_res,
        "ml": ml_res,
        "valuation_computation": val_res,
        "ingestion": ingest_res,
    }

    with open("optimized_benchmarks_output.json", "w") as f:
        json.dump(full_report, f, indent=2)

    print("\nBenchmark measurements successfully saved to optimized_benchmarks_output.json")
