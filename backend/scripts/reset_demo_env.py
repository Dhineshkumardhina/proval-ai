"""PropVal AI — Controlled Institutional Demonstration Environment Reset CLI.

Resets database tables, reseeds standard synthetic demonstration property cases,
recalculates baseline valuations, and initializes a verified cryptographic SHA-256 audit chain.
"""

import os
import sys
import logging
from sqlalchemy import text

# Add backend root to path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import Base, engine, SessionLocal
from app.core.seed import seed_demonstration_cases
from app.services.audit_service import verify_audit_chain
from app.core.security import DEMO_USERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("propval.demo_reset")


def reset_demonstration_environment():
    """Execute complete reset and reseed of demonstration database."""
    logger.info("=================================================================")
    logger.info("PropVal AI: Initializing Controlled Demonstration Environment")
    logger.info("=================================================================")

    db = SessionLocal()
    try:
        # 1. Clean existing records in reverse dependency order
        logger.info("Phase 1: Purging transient demonstration and test records...")
        table_order = [
            "ai_audit_logs",
            "audit_events",
            "duplicate_records",
            "rejected_records",
            "imported_transactions",
            "data_quality_reports",
            "datasets",
            "conformal_calibrations",
            "ml_models",
            "valuation_results",
            "valuation_cases",
            "properties",
        ]
        
        for table in table_order:
            try:
                db.execute(text(f"DELETE FROM {table}"))
            except Exception as e:
                logger.debug("Table %s purge notice: %s", table, e)
        db.commit()
        logger.info("Purged historical operational tables successfully.")

        # 2. Reseed Standard Demonstration Cases & Initialize Audit Trail
        logger.info("Phase 2: Seeding 6 canonical multi-metro demonstration dossiers...")
        count = seed_demonstration_cases(db)
        logger.info("Successfully populated %d demonstration property dossiers.", count)

        # 3. Verify Cryptographic Audit Chain Integrity
        logger.info("Phase 3: Verifying SHA-256 cryptographic audit chain genesis...")
        report = verify_audit_chain(db)
        logger.info("Audit Chain Status: %s (Verified %d genesis blocks)", 
                    "VALID" if report.is_valid else "INVALID", report.total_events)
        assert report.is_valid, "Audit chain integrity verification failed!"

        logger.info("=================================================================")
        logger.info("DEMONSTRATION ENVIRONMENT READY FOR INSTITUTIONAL PRESENTATION")
        logger.info("=================================================================")
        logger.info("Provisioned Demonstration User Roles:")
        for username, user_info in DEMO_USERS.items():
            if username in ("underwriter", "v.sundaram", "committee", "admin"):
                logger.info("  - Role: %-25s | Officer: %-30s | Username: %s", 
                            user_info["role"], user_info["name"], user_info["username"])
        logger.info("=================================================================")

    except Exception as exc:
        db.rollback()
        logger.error("Demonstration environment reset failed: %s", str(exc), exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    reset_demonstration_environment()

