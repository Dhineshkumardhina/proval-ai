"""Statistical anomaly and outlier detection engine for property transactions."""

import math
from typing import Any, Dict, List, Optional, Tuple

# Indian Micro-Market Admissible Valuation Bounds
MIN_PHYSICAL_CARPET_SQFT = 75.0
MAX_PHYSICAL_CARPET_SQFT = 35000.0

MIN_PLAUSIBLE_CONSIDERATION_INR = 250000.0  # ₹2.5 Lakhs
MAX_PLAUSIBLE_CONSIDERATION_INR = 2500000000.0  # ₹250 Crores

MIN_PRICE_PER_SQFT_INR = 1200.0  # Rural/Periphery floor
MAX_PRICE_PER_SQFT_INR = 250000.0  # Ultra-luxury prime floor (e.g. Malabar Hill / Worli / BKC)

# City-Specific Micro-Market Plausibility Price Bands (INR / sqft)
CITY_PRICE_PER_SQFT_BANDS: Dict[str, Tuple[float, float]] = {
    "Mumbai": (4500.0, 250000.0),
    "Bengaluru": (2500.0, 120000.0),
    "Bangalore": (2500.0, 120000.0),
    "Pune": (2200.0, 90000.0),
    "Delhi": (2800.0, 150000.0),
    "Noida": (2500.0, 85000.0),
    "Gurugram": (3000.0, 140000.0),
    "Gurgaon": (3000.0, 140000.0),
    "Hyderabad": (2200.0, 100000.0),
    "Chennai": (2500.0, 95000.0),
    "Kolkata": (1800.0, 80000.0),
    "Ahmedabad": (1800.0, 75000.0),
}


class AnomalyVerdict:
    """Represents the outcome of statistical, physical, and fraud anomaly checks."""

    def __init__(
        self,
        is_anomalous: bool,
        quarantine_code: Optional[str] = None,
        quarantine_reason: Optional[str] = None,
        anomaly_score: float = 0.0,
        anomalous_fields: Optional[List[str]] = None,
        fraud_risk_level: str = "LOW",
    ):
        self.is_anomalous = is_anomalous
        self.quarantine_code = quarantine_code
        self.quarantine_reason = quarantine_reason
        self.anomaly_score = anomaly_score
        self.anomalous_fields = anomalous_fields or []
        self.fraud_risk_level = fraud_risk_level


class TransactionAnomalyDetector:
    """Performs multi-dimensional statistical, physical, area-consistency, and fraud sanity checks."""

    @staticmethod
    def inspect(record: Dict[str, Any]) -> AnomalyVerdict:
        anomalies: List[str] = []
        score = 0.0
        code = None
        fraud_risk = "LOW"

        area = float(record.get("carpet_area_sqft") or 0.0)
        bua = float(record.get("built_up_area_sqft") or 0.0) if record.get("built_up_area_sqft") is not None else None
        sbua = float(record.get("super_built_up_area_sqft") or 0.0) if record.get("super_built_up_area_sqft") is not None else None
        price = float(record.get("transaction_price") or record.get("transaction_amount") or 0.0)
        rate = round(price / area, 2) if area > 0 and price > 0 else 0.0
        city = str(record.get("city") or record.get("district") or "").strip()

        # 1. Physical Area Boundary Anomaly
        if area > 0 and (area < MIN_PHYSICAL_CARPET_SQFT or area > MAX_PHYSICAL_CARPET_SQFT):
            anomalies.append(f"Carpet area ({area:.1f} sqft) outside physical bounds [{MIN_PHYSICAL_CARPET_SQFT}-{MAX_PHYSICAL_CARPET_SQFT}]")
            score += 0.4
            code = code or "AREA_ANOMALY"

        # 2. Area Consistency Checks (Carpet <= Built-up <= Super Built-up)
        if bua is not None and bua > 0 and area > 0:
            if area > bua:
                anomalies.append(f"Area consistency failure: Carpet area ({area:.1f} sqft) strictly exceeds built-up area ({bua:.1f} sqft)")
                score += 0.45
                code = code or "AREA_CONSISTENCY_INCONSISTENT"

        if sbua is not None and sbua > 0 and area > 0:
            if area > sbua:
                anomalies.append(f"Area consistency failure: Carpet area ({area:.1f} sqft) strictly exceeds super built-up area ({sbua:.1f} sqft)")
                score += 0.45
                code = code or "SUPER_BUILT_UP_INCONSISTENCY"
            elif bua is not None and bua > sbua:
                anomalies.append(f"Area consistency failure: Built-up area ({bua:.1f} sqft) exceeds super built-up area ({sbua:.1f} sqft)")
                score += 0.45
                code = code or "SUPER_BUILT_UP_INCONSISTENCY"
            else:
                # Loading factor check (SBUA / Carpet)
                loading = round(sbua / area, 2)
                if loading > 2.2 or loading < 1.02:
                    anomalies.append(f"Abnormal loading factor {loading:.2f} (expected range 1.05 - 2.0 for standard Indian apartments)")
                    score += 0.35
                    code = code or "ABNORMAL_LOADING_FACTOR"

        # 3. Consideration Bounds Anomaly
        if price > 0 and (price < MIN_PLAUSIBLE_CONSIDERATION_INR or price > MAX_PLAUSIBLE_CONSIDERATION_INR):
            anomalies.append(f"Transaction price (₹{price:,.0f}) outside plausible bounds")
            score += 0.35
            code = code or "PRICE_ANOMALY"

        # 4. Unit Rate (Price per SqFt) Outlier Anomaly
        if rate > 0 and (rate < MIN_PRICE_PER_SQFT_INR or rate > MAX_PRICE_PER_SQFT_INR):
            anomalies.append(f"Rate ₹{rate:,.0f}/sqft is an extreme outlier [{MIN_PRICE_PER_SQFT_INR}-{MAX_PRICE_PER_SQFT_INR}]")
            score += 0.45
            code = code or "RATE_OUTLIER_ANOMALY"
        elif rate > 0 and city in CITY_PRICE_PER_SQFT_BANDS:
            c_min, c_max = CITY_PRICE_PER_SQFT_BANDS[city]
            if rate < c_min or rate > c_max:
                anomalies.append(f"Rate ₹{rate:,.0f}/sqft deviates from {city} micro-market range [₹{c_min:,.0f}-₹{c_max:,.0f}]")
                score += 0.35
                code = code or "MICRO_MARKET_OUTLIER"

        # 5. Fraud Indicators: Circle Rate Evasion & Benami / Money Laundering Premium
        guideline = record.get("guideline_rate_per_sqft")
        if guideline is not None and float(guideline) > 0 and rate > 0:
            g_rate = float(guideline)
            dev_pct = ((rate - g_rate) / g_rate) * 100.0
            if dev_pct < -30.0:
                anomalies.append(f"Deed price is {abs(dev_pct):.1f}% below statutory circle rate (Stamp Duty Undervaluation Alert)")
                score += 0.50
                code = code or "CIRCLE_RATE_UNDERVALUATION"
                fraud_risk = "HIGH"
            elif dev_pct > 250.0:
                anomalies.append(f"Deed price is {dev_pct:.1f}% above statutory circle rate (Extreme Speculation / Benami Alert)")
                score += 0.40
                code = code or "CIRCLE_RATE_EXTREME_PREMIUM"
                fraud_risk = "MEDIUM"

        # 6. Fraud Indicators: Suspicious Round-Number Pricing on Fractional Areas
        if price >= 1000000 and price % 1000000 == 0 and area > 0 and (area % 1.0 > 0.05 and area % 1.0 < 0.95):
            anomalies.append("Suspicious round consideration (exact multiple of ₹10 Lakhs on fractional carpet area)")
            score += 0.20
            if fraud_risk == "LOW":
                fraud_risk = "EVALUATE"

        # 7. Floor Level Inconsistency
        floor_no = record.get("floor_number") or record.get("floor_no")
        total_floors = record.get("total_floors")
        if floor_no is not None and total_floors is not None:
            try:
                f_int = int(floor_no)
                t_int = int(total_floors)
                if f_int > t_int and t_int > 0:
                    anomalies.append(f"Floor number ({f_int}) exceeds total building floors ({t_int})")
                    score += 0.35
                    code = code or "PHYSICAL_STRUCTURE_INCONSISTENCY"
            except (ValueError, TypeError):
                pass

        # 8. Geographic Centroid Consistency
        lat = record.get("latitude")
        lon = record.get("longitude")
        if lat is not None and lon is not None and city:
            from app.normalization.geo_normalizer import validate_locality_spatial_consistency
            try:
                is_geo_consistent, geo_err = validate_locality_spatial_consistency(
                    latitude=float(lat),
                    longitude=float(lon),
                    city=city,
                )
                if not is_geo_consistent:
                    anomalies.append(geo_err or "Coordinates fall outside municipal urban bounds")
                    score += 0.45
                    code = code or "SPATIAL_OUTLIER_ANOMALY"
            except Exception:
                pass

        is_anom = score >= 0.4
        return AnomalyVerdict(
            is_anomalous=is_anom,
            quarantine_code=code,
            quarantine_reason="; ".join(anomalies) if anomalies else None,
            anomaly_score=round(min(1.0, score), 2),
            anomalous_fields=anomalies,
            fraud_risk_level=fraud_risk,
        )

