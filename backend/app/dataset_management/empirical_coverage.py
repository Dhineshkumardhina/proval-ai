"""Empirical Property Transaction Coverage & ML Eligibility Tracking Service (Phase 4C).

Tracks institutional progress toward the mandatory 1,000 verified empirical deed threshold
across city, locality, property type, transaction period, size, and price brackets.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.dataset import ImportedTransactionModel


class EmpiricalCoverageService:
    """Computes comprehensive empirical coverage metrics for institutional real estate valuation."""

    EMPIRICAL_TARGET_THRESHOLD = 1000

    @classmethod
    def get_empirical_coverage(cls, db: Session) -> Dict[str, Any]:
        """Aggregate certified empirical property transaction deeds across all required dimensions.

        Strictly excludes synthetic, mock, and unverified records.
        """
        # Base query for certified empirical deeds only
        base_query = (
            db.query(ImportedTransactionModel)
            .filter(
                ImportedTransactionModel.is_verified_deed == True,
                ImportedTransactionModel.is_asking_price == False,
                ImportedTransactionModel.data_source != "synthetic-demo",
                ImportedTransactionModel.data_source != "synthetic_benchmark",
                ~ImportedTransactionModel.data_source.ilike("%mock%"),
                ~ImportedTransactionModel.data_source.ilike("%test%"),
                ~ImportedTransactionModel.data_source.ilike("%simulation%"),
            )
        )

        total_empirical = base_query.count()
        is_eligible = total_empirical >= cls.EMPIRICAL_TARGET_THRESHOLD
        progress_pct = round(min(100.0, (total_empirical / cls.EMPIRICAL_TARGET_THRESHOLD) * 100.0), 1)

        # 1. City Coverage
        city_rows = (
            base_query.with_entities(
                ImportedTransactionModel.city,
                func.count(ImportedTransactionModel.id).label("count"),
            )
            .group_by(ImportedTransactionModel.city)
            .order_by(desc("count"))
            .all()
        )
        city_distribution = [
            {
                "city": r[0],
                "count": r[1],
                "percentage": round((r[1] / total_empirical) * 100.0, 1) if total_empirical > 0 else 0.0,
            }
            for r in city_rows
        ]

        # 2. Locality Coverage
        locality_count = (
            base_query.with_entities(ImportedTransactionModel.locality)
            .distinct()
            .count()
        )
        top_localities_rows = (
            base_query.with_entities(
                ImportedTransactionModel.locality,
                ImportedTransactionModel.city,
                func.count(ImportedTransactionModel.id).label("count"),
            )
            .group_by(ImportedTransactionModel.locality, ImportedTransactionModel.city)
            .order_by(desc("count"))
            .limit(20)
            .all()
        )
        top_localities = [
            {"locality": r[0], "city": r[1], "count": r[2]}
            for r in top_localities_rows
        ]

        # 3. Property Type Breakdown
        prop_rows = (
            base_query.with_entities(
                ImportedTransactionModel.property_type,
                func.count(ImportedTransactionModel.id).label("count"),
            )
            .group_by(ImportedTransactionModel.property_type)
            .order_by(desc("count"))
            .all()
        )
        property_type_distribution = [
            {
                "property_type": r[0],
                "count": r[1],
                "percentage": round((r[1] / total_empirical) * 100.0, 1) if total_empirical > 0 else 0.0,
            }
            for r in prop_rows
        ]

        # 4. Transaction Period (by Quarter)
        quarter_rows = (
            base_query.with_entities(
                ImportedTransactionModel.transaction_quarter,
                func.count(ImportedTransactionModel.id).label("count"),
            )
            .group_by(ImportedTransactionModel.transaction_quarter)
            .order_by(ImportedTransactionModel.transaction_quarter.asc())
            .all()
        )
        period_distribution = [
            {"quarter": r[0], "count": r[1]}
            for r in quarter_rows
        ]

        # 5. Property Size Brackets (sqft)
        size_brackets = {
            "Under 500 sqft": base_query.filter(ImportedTransactionModel.carpet_area_sqft < 500).count(),
            "500 - 1,000 sqft": base_query.filter(ImportedTransactionModel.carpet_area_sqft >= 500, ImportedTransactionModel.carpet_area_sqft < 1000).count(),
            "1,000 - 1,500 sqft": base_query.filter(ImportedTransactionModel.carpet_area_sqft >= 1000, ImportedTransactionModel.carpet_area_sqft < 1500).count(),
            "1,500 - 2,500 sqft": base_query.filter(ImportedTransactionModel.carpet_area_sqft >= 1500, ImportedTransactionModel.carpet_area_sqft < 2500).count(),
            "2,500+ sqft": base_query.filter(ImportedTransactionModel.carpet_area_sqft >= 2500).count(),
        }

        # 6. Price Range Brackets (INR)
        price_brackets = {
            "Under ₹50 Lakhs": base_query.filter(ImportedTransactionModel.transaction_price < 5000000).count(),
            "₹50L - ₹1 Crore": base_query.filter(ImportedTransactionModel.transaction_price >= 5000000, ImportedTransactionModel.transaction_price < 10000000).count(),
            "₹1Cr - ₹2.5 Crores": base_query.filter(ImportedTransactionModel.transaction_price >= 10000000, ImportedTransactionModel.transaction_price < 25000000).count(),
            "₹2.5Cr - ₹5 Crores": base_query.filter(ImportedTransactionModel.transaction_price >= 25000000, ImportedTransactionModel.transaction_price < 50000000).count(),
            "₹5+ Crores": base_query.filter(ImportedTransactionModel.transaction_price >= 50000000).count(),
        }

        return {
            "total_verified_empirical_deeds": total_empirical,
            "target_threshold": cls.EMPIRICAL_TARGET_THRESHOLD,
            "progress_percentage": progress_pct,
            "ml_eligibility_status": "ELIGIBLE" if is_eligible else "GATED",
            "eligibility_message": (
                f"Empirical cohort: {total_empirical} / {cls.EMPIRICAL_TARGET_THRESHOLD} verified deeds. "
                + ("Minimum empirical training eligibility threshold reached." if is_eligible else "Model training is strictly blocked until ≥ 1,000 empirical deeds are accumulated.")
            ),
            "total_unique_localities_covered": locality_count,
            "city_distribution": city_distribution,
            "top_localities": top_localities,
            "property_type_distribution": property_type_distribution,
            "period_distribution": period_distribution,
            "property_size_brackets": size_brackets,
            "price_range_brackets": price_brackets,
        }

