"""phase6d_postgresql_native_rls

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-05 23:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RLS_TABLES = [
    'valuation_cases',
    'properties',
    'valuation_results',
    'institution_policies',
    'institutions',
    'audit_events',
    'ai_audit_logs',
]


def upgrade() -> None:
    """Implement PostgreSQL Native Row-Level Security (RLS) policies and tenant ownership columns."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Add tenant ownership columns to tables missing direct institution_id
    insp = sa.inspect(bind)
    prop_cols = [c['name'] for c in insp.get_columns('properties')]
    if 'institution_id' not in prop_cols:
        with op.batch_alter_table('properties', schema=None) as batch_op:
            batch_op.add_column(sa.Column('institution_id', sa.String(length=36), nullable=True))
            batch_op.create_index('ix_properties_institution_id', ['institution_id'])
            if is_postgres:
                batch_op.create_foreign_key('fk_properties_institution_id', 'institutions', ['institution_id'], ['id'], ondelete='SET NULL')

    val_cols = [c['name'] for c in insp.get_columns('valuation_results')]
    if 'institution_id' not in val_cols:
        with op.batch_alter_table('valuation_results', schema=None) as batch_op:
            batch_op.add_column(sa.Column('institution_id', sa.String(length=36), nullable=True))
            batch_op.create_index('ix_valuation_results_institution_id', ['institution_id'])
            if is_postgres:
                batch_op.create_foreign_key('fk_valuation_results_institution_id', 'institutions', ['institution_id'], ['id'], ondelete='CASCADE')

    ai_cols = [c['name'] for c in insp.get_columns('ai_audit_logs')]
    if 'institution_id' not in ai_cols:
        with op.batch_alter_table('ai_audit_logs', schema=None) as batch_op:
            batch_op.add_column(sa.Column('institution_id', sa.String(length=36), nullable=True))
            batch_op.create_index('ix_ai_audit_logs_institution_id', ['institution_id'])
            if is_postgres:
                batch_op.create_foreign_key('fk_ai_audit_logs_institution_id', 'institutions', ['institution_id'], ['id'], ondelete='CASCADE')

    # 2. Database-Native PostgreSQL Row-Level Security (RLS) Policies
    if is_postgres:
        # Standard Tenant Isolation Policy Template:
        # 1. Platform Admin bypass: current_setting('app.is_platform_admin', true) = 'true'
        # 2. Matching Tenant Context: institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
        # 3. Missing/Empty context: Fails closed (evaluates to NULL / False).

        # Enable & Force RLS on valuation_cases
        op.execute("ALTER TABLE valuation_cases ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE valuation_cases FORCE ROW LEVEL SECURITY;")
        op.execute("""
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
        """)

        # Enable & Force RLS on properties
        op.execute("ALTER TABLE properties ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE properties FORCE ROW LEVEL SECURITY;")
        op.execute("""
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
        """)

        # Enable & Force RLS on valuation_results
        op.execute("ALTER TABLE valuation_results ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE valuation_results FORCE ROW LEVEL SECURITY;")
        op.execute("""
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
        """)

        # Enable & Force RLS on institution_policies
        op.execute("ALTER TABLE institution_policies ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE institution_policies FORCE ROW LEVEL SECURITY;")
        op.execute("""
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
        """)

        # Enable & Force RLS on institutions (tenant can only see own record; admin can see all)
        op.execute("ALTER TABLE institutions ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE institutions FORCE ROW LEVEL SECURITY;")
        op.execute("""
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
        """)

        # Enable & Force RLS on audit_events
        # Read: Own institution or platform admin or compliance auditor
        # Insert: Own institution or admin
        op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;")
        op.execute("""
            CREATE POLICY audit_events_tenant_select ON audit_events
            FOR SELECT
            USING (
                current_setting('app.is_platform_admin', true) = 'true'
                OR current_setting('app.is_compliance_auditor', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            );
        """)
        op.execute("""
            CREATE POLICY audit_events_tenant_insert ON audit_events
            FOR INSERT
            WITH CHECK (
                current_setting('app.is_platform_admin', true) = 'true'
                OR institution_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            );
        """)

        # Enable & Force RLS on ai_audit_logs
        op.execute("ALTER TABLE ai_audit_logs ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE ai_audit_logs FORCE ROW LEVEL SECURITY;")
        op.execute("""
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
        """)


def downgrade() -> None:
    """Drop PostgreSQL RLS policies and revert schema changes."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP POLICY IF EXISTS ai_audit_logs_tenant_isolation ON ai_audit_logs;")
        op.execute("ALTER TABLE ai_audit_logs NO FORCE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE ai_audit_logs DISABLE ROW LEVEL SECURITY;")

        op.execute("DROP POLICY IF EXISTS audit_events_tenant_insert ON audit_events;")
        op.execute("DROP POLICY IF EXISTS audit_events_tenant_select ON audit_events;")
        op.execute("ALTER TABLE audit_events NO FORCE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY;")

        op.execute("DROP POLICY IF EXISTS institutions_tenant_isolation ON institutions;")
        op.execute("ALTER TABLE institutions NO FORCE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE institutions DISABLE ROW LEVEL SECURITY;")

        op.execute("DROP POLICY IF EXISTS institution_policies_tenant_isolation ON institution_policies;")
        op.execute("ALTER TABLE institution_policies NO FORCE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE institution_policies DISABLE ROW LEVEL SECURITY;")

        op.execute("DROP POLICY IF EXISTS valuation_results_tenant_isolation ON valuation_results;")
        op.execute("ALTER TABLE valuation_results NO FORCE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE valuation_results DISABLE ROW LEVEL SECURITY;")

        op.execute("DROP POLICY IF EXISTS properties_tenant_isolation ON properties;")
        op.execute("ALTER TABLE properties NO FORCE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE properties DISABLE ROW LEVEL SECURITY;")

        op.execute("DROP POLICY IF EXISTS valuation_cases_tenant_isolation ON valuation_cases;")
        op.execute("ALTER TABLE valuation_cases NO FORCE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE valuation_cases DISABLE ROW LEVEL SECURITY;")

    with op.batch_alter_table('ai_audit_logs', schema=None) as batch_op:
        batch_op.drop_column('institution_id')

    with op.batch_alter_table('valuation_results', schema=None) as batch_op:
        batch_op.drop_column('institution_id')

    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.drop_column('institution_id')

