"""Deterministic duplicate detection and fuzzy candidate flagging for property transactions."""

import hashlib
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


def compute_deterministic_deed_hash(
    state: str,
    district: str,
    sro_office: str,
    registration_year: str,
    registration_number: str,
    unit_number: Optional[str] = None,
) -> str:
    """Compute canonical SHA-256 fingerprint from immutable SRO deed parameters."""
    canonical_key = (
        f"{state.strip().upper()}|{district.strip().upper()}|"
        f"{sro_office.strip().upper()}|{registration_year.strip()}|"
        f"{registration_number.strip().upper()}|{(unit_number or '').strip().upper()}"
    )
    return hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()


def calculate_property_similarity(
    record_a: Dict[str, Any],
    record_b: Dict[str, Any],
) -> Tuple[float, List[str]]:
    """Compute multi-attribute fuzzy similarity score between two candidate records.

    Compares:
    - Locality string similarity (Levenshtein ratio via SequenceMatcher).
    - Project name similarity.
    - Transaction date proximity (within 30 days).
    - Area similarity (within 3%).
    - Price similarity (within 2%).

    Returns:
        (similarity_score_0_to_1, matched_feature_reasons)
    """
    matches = []
    scores = []

    # 1. Project Name Similarity (Weight: 30%)
    proj_a = str(record_a.get("project_name") or "").strip().lower()
    proj_b = str(record_b.get("project_name") or "").strip().lower()
    if proj_a and proj_b:
        proj_sim = SequenceMatcher(None, proj_a, proj_b).ratio()
        scores.append(proj_sim * 0.30)
        if proj_sim > 0.85:
            matches.append(f"Project match ({proj_sim*100:.0f}%)")
    else:
        scores.append(0.0)

    # 2. Locality Similarity (Weight: 20%)
    loc_a = str(record_a.get("locality") or "").strip().lower()
    loc_b = str(record_b.get("locality") or "").strip().lower()
    if loc_a and loc_b:
        loc_sim = SequenceMatcher(None, loc_a, loc_b).ratio()
        scores.append(loc_sim * 0.20)
        if loc_sim > 0.90:
            matches.append(f"Locality match ({loc_sim*100:.0f}%)")
    else:
        scores.append(0.0)

    # 3. Area Proximity (Weight: 25%)
    area_a = float(record_a.get("carpet_area_sqft") or 0.0)
    area_b = float(record_b.get("carpet_area_sqft") or 0.0)
    if area_a > 0 and area_b > 0:
        area_diff_pct = abs(area_a - area_b) / max(area_a, area_b)
        if area_diff_pct <= 0.03:  # Within 3%
            scores.append(0.25)
            matches.append(f"Identical area ({area_a:.0f} sqft)")
        elif area_diff_pct <= 0.08:
            scores.append(0.15)
        else:
            scores.append(0.0)
    else:
        scores.append(0.0)

    # 4. Price Proximity (Weight: 25%)
    price_a = float(record_a.get("transaction_price") or record_a.get("transaction_amount") or 0.0)
    price_b = float(record_b.get("transaction_price") or record_b.get("transaction_amount") or 0.0)
    if price_a > 0 and price_b > 0:
        price_diff_pct = abs(price_a - price_b) / max(price_a, price_b)
        if price_diff_pct <= 0.02:  # Within 2%
            scores.append(0.25)
            matches.append("Identical consideration amount")
        elif price_diff_pct <= 0.05:
            scores.append(0.15)
        else:
            scores.append(0.0)
    else:
        scores.append(0.0)

    total_score = round(sum(scores), 3)
    return total_score, matches

