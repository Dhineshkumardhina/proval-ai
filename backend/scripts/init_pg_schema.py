"""Initialize PostgreSQL Test Database Schema with Native Row-Level Security (RLS)."""

import os
import subprocess
import psycopg2
from sqlalchemy import create_engine, text
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import Base
import app.models  # load all models

def get_pg_url():
    # Detect WSL IP
    try:
        wsl_ip = subprocess.check_output(['wsl', '-e', 'hostname', '-I']).decode().split()[0]
    except Exception:
        wsl_ip = "127.0.0.1"
    return f"postgresql+psycopg2://propval_user:propval_password@{wsl_ip}:5432/propval_test"

def init_postgres():
    url = get_pg_url()
    print(f"Connecting to PostgreSQL at {url}...")
    engine = create_engine(url)

    # 1. Drop existing schema cascade and recreate cleanly
    print("Recreating public schema and all tables from SQLAlchemy Base metadata...")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"))
        conn.commit()
    Base.metadata.create_all(engine)
    print("Tables created successfully!")

    # 2. Create non-superuser application role 'propval_app_user' for strict RLS enforcement
    with engine.connect() as conn:
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'propval_app_user') THEN
                    CREATE ROLE propval_app_user WITH LOGIN PASSWORD 'app_user_password' NOSUPERUSER NOBYPASSRLS;
                END IF;
            END
            $$;
        """))
        conn.execute(text("GRANT ALL ON SCHEMA public TO propval_app_user;"))
        conn.execute(text("GRANT ALL ON ALL TABLES IN SCHEMA public TO propval_app_user;"))
        conn.execute(text("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO propval_app_user;"))
        conn.commit()
    print("Application role 'propval_app_user' configured with NOBYPASSRLS!")

    # 3. Apply Row-Level Security Policies across all tenant tables
    with engine.connect() as conn:
        # A. valuation_cases
        conn.execute(text("ALTER TABLE valuation_cases ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE valuation_cases FORCE ROW LEVEL SECURITY;"))
        conn.execute(text("DROP POLICY IF EXISTS valuation_cases_tenant_isolation ON valuation_cases;"))
        conn.execute(text("""
            CREATE POLICY valuation_cases_tenant_isolation ON valuation_cases
            FOR ALL
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            )
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            );
        """))

        # B. properties
        conn.execute(text("ALTER TABLE properties ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE properties FORCE ROW LEVEL SECURITY;"))
        conn.execute(text("DROP POLICY IF EXISTS properties_tenant_isolation ON properties;"))
        conn.execute(text("""
            CREATE POLICY properties_tenant_isolation ON properties
            FOR ALL
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
                OR institution_id IS NULL
            )
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            );
        """))

        # C. valuation_results
        conn.execute(text("ALTER TABLE valuation_results ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE valuation_results FORCE ROW LEVEL SECURITY;"))
        conn.execute(text("DROP POLICY IF EXISTS valuation_results_tenant_isolation ON valuation_results;"))
        conn.execute(text("""
            CREATE POLICY valuation_results_tenant_isolation ON valuation_results
            FOR ALL
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
                OR case_id IN (
                    SELECT id FROM valuation_cases
                    WHERE institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
                )
            )
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
                OR case_id IN (
                    SELECT id FROM valuation_cases
                    WHERE institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
                )
            );
        """))

        # D. institution_policies
        conn.execute(text("ALTER TABLE institution_policies ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE institution_policies FORCE ROW LEVEL SECURITY;"))
        conn.execute(text("DROP POLICY IF EXISTS institution_policies_tenant_isolation ON institution_policies;"))
        conn.execute(text("""
            CREATE POLICY institution_policies_tenant_isolation ON institution_policies
            FOR ALL
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            )
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            );
        """))

        # E. institutions
        conn.execute(text("ALTER TABLE institutions ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE institutions FORCE ROW LEVEL SECURITY;"))
        conn.execute(text("DROP POLICY IF EXISTS institutions_tenant_isolation ON institutions;"))
        conn.execute(text("""
            CREATE POLICY institutions_tenant_isolation ON institutions
            FOR ALL
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR id = NULLIF(current_setting('app.current_tenant_id', true), '')
            )
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
                OR id = NULLIF(current_setting('app.current_tenant_id', true), '')
            );
        """))

        # F. audit_events
        conn.execute(text("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;"))
        conn.execute(text("DROP POLICY IF EXISTS audit_events_tenant_select ON audit_events;"))
        conn.execute(text("DROP POLICY IF EXISTS audit_events_tenant_insert ON audit_events;"))
        conn.execute(text("""
            CREATE POLICY audit_events_tenant_select ON audit_events
            FOR SELECT
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR current_setting('app.is_compliance_auditor', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            );
        """))
        conn.execute(text("""
            CREATE POLICY audit_events_tenant_insert ON audit_events
            FOR INSERT
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            );
        """))

        # G. ai_audit_logs
        conn.execute(text("ALTER TABLE ai_audit_logs ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE ai_audit_logs FORCE ROW LEVEL SECURITY;"))
        conn.execute(text("DROP POLICY IF EXISTS ai_audit_logs_tenant_isolation ON ai_audit_logs;"))
        conn.execute(text("""
            CREATE POLICY ai_audit_logs_tenant_isolation ON ai_audit_logs
            FOR ALL
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
                OR case_id IN (
                    SELECT id FROM valuation_cases
                    WHERE institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
                )
            )
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            );
        """))

        conn.commit()

    print("PostgreSQL RLS Policies successfully enabled and forced across all tenant tables!")

if __name__ == "__main__":
    init_postgres()
