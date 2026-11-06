"""Asynchronous API endpoint latency and concurrent load benchmark for PropVal AI backend."""

import asyncio
import json
import os
import sys
import time
import httpx
import numpy as np
import psutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import SessionLocal, engine
from app.models.valuation import ValuationCaseModel

# Suppress verbose SQL logging during performance benchmarking
engine.echo = False

db = SessionLocal()
first_case = db.query(ValuationCaseModel).first()
case_id = first_case.id if first_case else "case-blr-89412"
db.close()


async def run_benchmarks():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Obtain authentication JWT token
        auth_resp = await client.post(
            "/api/v1/auth/token",
            json={"username": "v.sundaram", "password": "SrUnderwriter@2026!"},
        )
        if auth_resp.status_code != 200:
            raise RuntimeError(f"Authentication failed ({auth_resp.status_code}): {auth_resp.text}")
        token = auth_resp.json()["access_token"]

        # 2. Benchmark sequential endpoint latency
        val_payload = {
            "carpetAreaSqFt": 1200.0,
            "superBuiltUpAreaSqFt": 1560.0,
            "baseMarketRatePerSqFt": 12000.0,
            "circleRatePerSqFt": 9500.0,
            "floorRiseFactor": 350.0,
            "roadWidthFactor": 200.0,
            "amenitiesPremium": 400.0,
            "structuralDepreciation": 150.0,
            "underwriterHaircutPct": 10.0,
            "distressDiscountPct": 15.0,
            "ltvRatioPct": 75.0,
            "legalRiskPenaltyPct": 0.0,
        }

        endpoints = [
            ("GET", "/api/v1/health", None, None),
            ("GET", "/api/v1/cases", None, {"limit": 20}),
            ("GET", f"/api/v1/cases/{case_id}", None, None),
            ("POST", "/api/v1/valuation/estimate", val_payload, None),
            ("GET", "/api/v1/comparables", None, {"city": "Bengaluru"}),
            ("GET", "/api/v1/ml/status", None, None),
            ("GET", "/api/v1/ml/uncertainty/status", None, None),
            ("GET", "/api/v1/ai/status", None, None),
        ]

        print("=" * 65)
        print("BENCHMARKING SEQUENTIAL ENDPOINTS (30 requests each)")
        print("=" * 65)
        seq_results = []
        for ep_idx, (m, p, b, pr) in enumerate(endpoints):
            latencies = []
            codes = []
            # Each endpoint iteration simulates user from an institutional sub-branch IP
            for req_idx in range(30):
                req_headers = {
                    "Authorization": f"Bearer {token}",
                    "X-Forwarded-For": f"10.0.{ep_idx + 1}.{req_idx + 1}",
                }
                t0 = time.perf_counter()
                if m == "GET":
                    r = await client.get(p, headers=req_headers, params=pr)
                elif m == "POST":
                    r = await client.post(p, headers=req_headers, json=b)
                dur_ms = (time.perf_counter() - t0) * 1000
                latencies.append(dur_ms)
                codes.append(r.status_code)
            
            errors = sum(1 for c in codes if c >= 400)
            res = {
                "endpoint": f"{m} {p}",
                "iterations": 30,
                "mean_latency_ms": round(float(np.mean(latencies)), 2),
                "median_p50_ms": round(float(np.median(latencies)), 2),
                "p95_ms": round(float(np.percentile(latencies, 95)), 2),
                "p99_ms": round(float(np.percentile(latencies, 99)), 2),
                "min_ms": round(float(np.min(latencies)), 2),
                "max_ms": round(float(np.max(latencies)), 2),
                "error_rate_pct": round((errors / 30) * 100.0, 2),
            }
            seq_results.append(res)
            print(f"  {res['endpoint']}: mean={res['mean_latency_ms']}ms, p50={res['median_p50_ms']}ms, p95={res['p95_ms']}ms, err={res['error_rate_pct']}%")

        # 3. Concurrent request benchmarking across multiple concurrent users
        async def benchmark_concurrency(total_reqs, conc_level):
            sem = asyncio.Semaphore(conc_level)
            latencies = []
            errors = 0

            async def single_fetch(user_id: int):
                nonlocal errors
                user_headers = {
                    "Authorization": f"Bearer {token}",
                    "X-Forwarded-For": f"10.10.{(user_id % conc_level) + 1}.{((user_id // conc_level) % 250) + 1}",
                }
                async with sem:
                    t0 = time.perf_counter()
                    r = await client.get("/api/v1/cases?limit=20", headers=user_headers)
                    dur = (time.perf_counter() - t0) * 1000
                    latencies.append(dur)
                    if r.status_code >= 400:
                        errors += 1

            start_cpu = psutil.cpu_percent(interval=None)
            wall_start = time.perf_counter()
            tasks = [asyncio.create_task(single_fetch(i)) for i in range(total_reqs)]
            await asyncio.gather(*tasks)
            wall_dur = time.perf_counter() - wall_start
            end_cpu = psutil.cpu_percent(interval=None)
            end_mem = psutil.Process().memory_info().rss / (1024 * 1024)
            rps = total_reqs / wall_dur

            return {
                "concurrency_level": conc_level,
                "total_requests": total_reqs,
                "wall_duration_sec": round(wall_dur, 3),
                "throughput_rps": round(rps, 2),
                "mean_latency_ms": round(float(np.mean(latencies)), 2),
                "median_p50_ms": round(float(np.median(latencies)), 2),
                "p95_ms": round(float(np.percentile(latencies, 95)), 2),
                "p99_ms": round(float(np.percentile(latencies, 99)), 2),
                "error_rate_pct": round((errors / total_reqs) * 100.0, 2),
                "cpu_utilization_pct": end_cpu,
                "memory_rss_mb": round(end_mem, 2),
            }

        print("\nBENCHMARKING CONCURRENT LOAD (25 concurrent workers, 200 requests)...")
        conc_25 = await benchmark_concurrency(total_reqs=200, conc_level=25)
        print(json.dumps(conc_25, indent=2))

        print("\nBENCHMARKING HIGH CONCURRENT LOAD (50 concurrent workers, 250 requests)...")
        conc_50 = await benchmark_concurrency(total_reqs=250, conc_level=50)
        print(json.dumps(conc_50, indent=2))

        output = {
            "sequential_endpoints": seq_results,
            "concurrency_25": conc_25,
            "concurrency_50": conc_50,
        }

        with open("optimized_api_benchmarks_output.json", "w") as f:
            json.dump(output, f, indent=2)
        print("\nOptimized API benchmarks saved to optimized_api_benchmarks_output.json")


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
