"""phase5b_institutional_onboarding_and_multitenancy

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-05 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create institutions and institution_policies tables and add multi-tenancy columns."""
    # 1. Create institutions table
    op.create_table(
        'institutions',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('institution_type', sa.String(length=64), server_default='HFC', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='ACTIVE', nullable=True),
        sa.Column('cin_or_registration_no', sa.String(length=128), server_default='', nullable=True),
        sa.Column('rbi_nhb_registration_no', sa.String(length=128), server_default='', nullable=True),
        sa.Column('primary_contact_name', sa.String(length=128), server_default='', nullable=True),
        sa.Column('primary_contact_email', sa.String(length=255), nullable=False),
        sa.Column('primary_contact_phone', sa.String(length=32), server_default='', nullable=True),
        sa.Column('registered_office_address', sa.Text(), server_default='', nullable=True),
        sa.Column('branches', sa.JSON(), nullable=True),
        sa.Column('authorized_domains', sa.JSON(), nullable=True),
        sa.Column('retention_period_years', sa.Integer(), server_default='8', nullable=True),
        sa.Column('api_key_prefix', sa.String(length=16), nullable=True),
        sa.Column('api_key_hash', sa.String(length=64), nullable=True),
        sa.Column('webhook_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_institutions_code', 'institutions', ['code'], unique=True)
    op.create_index('ix_institutions_status', 'institutions', ['status'], unique=False)
    op.create_index('ix_institutions_code_status', 'institutions', ['code', 'status'], unique=False)

    # 2. Create institution_policies table
    op.create_table(
        'institution_policies',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('institution_id', sa.String(length=36), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('max_ltv_pct', sa.Float(), server_default='75.0', nullable=False),
        sa.Column('default_distress_discount_pct', sa.Float(), server_default='17.0', nullable=False),
        sa.Column('max_underwriter_haircut_pct', sa.Float(), server_default='25.0', nullable=False),
        sa.Column('circle_rate_tolerance_pct', sa.Float(), server_default='20.0', nullable=False),
        sa.Column('min_cibil_score', sa.Integer(), server_default='700', nullable=False),
        sa.Column('mandatory_title_search_years', sa.Integer(), server_default='30', nullable=False),
        sa.Column('require_rera_for_ongoing', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('require_nil_encumbrance', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('approval_hierarchy', sa.JSON(), nullable=True),
        sa.Column('audit_requirements', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_institution_policies_institution_id', 'institution_policies', ['institution_id'], unique=True)

    # 3. Add institution_id to valuation_cases
    with op.batch_alter_table('valuation_cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('institution_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key('fk_valuation_cases_institution_id', 'institutions', ['institution_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_valuation_cases_institution_id', ['institution_id'], unique=False)

    # 4. Add institution_id to audit_events
    with op.batch_alter_table('audit_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('institution_id', sa.String(length=36), nullable=True))
        batch_op.create_index('ix_audit_events_institution_id', ['institution_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('audit_events', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_events_institution_id')
        batch_op.drop_column('institution_id')

    with op.batch_alter_table('valuation_cases', schema=None) as batch_op:
        batch_op.drop_index('ix_valuation_cases_institution_id')
        batch_op.drop_column('institution_id')

    op.drop_index('ix_institution_policies_institution_id', table_name='institution_policies')
    op.drop_table('institution_policies')

    op.drop_index('ix_institutions_code_status', table_name='institutions')
    op.drop_index('ix_institutions_status', table_name='institutions')
    op.drop_index('ix_institutions_code', table_name='institutions')
    op.drop_table('institutions')
