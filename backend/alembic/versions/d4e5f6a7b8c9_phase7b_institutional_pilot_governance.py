"""phase7b_institutional_pilot_governance

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-06 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 7B institutional pilot agreements and case safety governance columns."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    inst_cols = [c['name'] for c in insp.get_columns('institutions')]

    # 1. Update institutions table
    with op.batch_alter_table('institutions') as batch_op:
        if 'agreement_status' not in inst_cols:
            batch_op.add_column(sa.Column('agreement_status', sa.String(length=32), server_default='PENDING', nullable=True))
        if 'agreement_reference' not in inst_cols:
            batch_op.add_column(sa.Column('agreement_reference', sa.String(length=128), server_default='', nullable=True))
        if 'agreement_signed_date' not in inst_cols:
            batch_op.add_column(sa.Column('agreement_signed_date', sa.DateTime(timezone=True), nullable=True))
        if 'agreement_signatory_name' not in inst_cols:
            batch_op.add_column(sa.Column('agreement_signatory_name', sa.String(length=128), server_default='', nullable=True))
        if 'agreement_signatory_title' not in inst_cols:
            batch_op.add_column(sa.Column('agreement_signatory_title', sa.String(length=128), server_default='', nullable=True))
        if 'agreement_evidence_url' not in inst_cols:
            batch_op.add_column(sa.Column('agreement_evidence_url', sa.String(length=500), server_default='', nullable=True))

        if 'dpa_status' not in inst_cols:
            batch_op.add_column(sa.Column('dpa_status', sa.String(length=32), server_default='PENDING', nullable=True))
        if 'dpa_reference' not in inst_cols:
            batch_op.add_column(sa.Column('dpa_reference', sa.String(length=128), server_default='', nullable=True))
        if 'dpa_signed_date' not in inst_cols:
            batch_op.add_column(sa.Column('dpa_signed_date', sa.DateTime(timezone=True), nullable=True))
        if 'dpa_signatory_name' not in inst_cols:
            batch_op.add_column(sa.Column('dpa_signatory_name', sa.String(length=128), server_default='', nullable=True))

        if 'pilot_authorization_status' not in inst_cols:
            batch_op.add_column(sa.Column('pilot_authorization_status', sa.String(length=32), server_default='UNAUTHORIZED', nullable=True))
        if 'pilot_commencement_date' not in inst_cols:
            batch_op.add_column(sa.Column('pilot_commencement_date', sa.DateTime(timezone=True), nullable=True))
        if 'pilot_expiry_date' not in inst_cols:
            batch_op.add_column(sa.Column('pilot_expiry_date', sa.DateTime(timezone=True), nullable=True))
        if 'authorized_pilot_participants' not in inst_cols:
            batch_op.add_column(sa.Column('authorized_pilot_participants', sa.JSON(), nullable=True))
        if 'approved_data_categories' not in inst_cols:
            batch_op.add_column(sa.Column('approved_data_categories', sa.JSON(), nullable=True))
        if 'permitted_purposes' not in inst_cols:
            batch_op.add_column(sa.Column('permitted_purposes', sa.JSON(), nullable=True))
        if 'approved_operational_scope' not in inst_cols:
            batch_op.add_column(sa.Column('approved_operational_scope', sa.JSON(), nullable=True))
        if 'approval_evidence_reference' not in inst_cols:
            batch_op.add_column(sa.Column('approval_evidence_reference', sa.String(length=255), server_default='', nullable=True))
        if 'is_pilot_approved' not in inst_cols:
            batch_op.add_column(sa.Column('is_pilot_approved', sa.Boolean(), server_default=sa.text('0'), nullable=True))

    case_cols = [c['name'] for c in insp.get_columns('valuation_cases')]
    # 2. Update valuation_cases table
    with op.batch_alter_table('valuation_cases') as batch_op:
        if 'case_reference' not in case_cols:
            batch_op.add_column(sa.Column('case_reference', sa.String(length=64), nullable=True))
        if 'assigned_valuer' not in case_cols:
            batch_op.add_column(sa.Column('assigned_valuer', sa.String(length=128), server_default='Empaneled Field Valuer', nullable=True))
        if 'reviewing_credit_officer' not in case_cols:
            batch_op.add_column(sa.Column('reviewing_credit_officer', sa.String(length=128), server_default='', nullable=True))
        if 'valuation_engine_version' not in case_cols:
            batch_op.add_column(sa.Column('valuation_engine_version', sa.String(length=32), server_default='hedonic-scorecard-v0.2.0', nullable=True))
        if 'valuation_methodology' not in case_cols:
            batch_op.add_column(sa.Column('valuation_methodology', sa.String(length=64), server_default='DETERMINISTIC_HEDONIC', nullable=True))
        if 'advisory_classification' not in case_cols:
            batch_op.add_column(sa.Column('advisory_classification', sa.String(length=32), server_default='ADVISORY_ONLY', nullable=True))
        if 'divergence_pct' not in case_cols:
            batch_op.add_column(sa.Column('divergence_pct', sa.Float(), server_default='0.0', nullable=True))
        if 'requires_senior_review' not in case_cols:
            batch_op.add_column(sa.Column('requires_senior_review', sa.Boolean(), server_default=sa.text('0'), nullable=True))
        if 'human_sign_off_by' not in case_cols:
            batch_op.add_column(sa.Column('human_sign_off_by', sa.String(length=128), nullable=True))
        if 'human_sign_off_date' not in case_cols:
            batch_op.add_column(sa.Column('human_sign_off_date', sa.DateTime(timezone=True), nullable=True))
        if 'human_sign_off_notes' not in case_cols:
            batch_op.add_column(sa.Column('human_sign_off_notes', sa.String(length=1000), server_default='', nullable=True))


def downgrade() -> None:
    """Revert Phase 7B columns."""
    with op.batch_alter_table('valuation_cases') as batch_op:
        batch_op.drop_index('ix_valuation_cases_case_reference')
        batch_op.drop_column('human_sign_off_notes')
        batch_op.drop_column('human_sign_off_date')
        batch_op.drop_column('human_sign_off_by')
        batch_op.drop_column('requires_senior_review')
        batch_op.drop_column('divergence_pct')
        batch_op.drop_column('advisory_classification')
        batch_op.drop_column('valuation_methodology')
        batch_op.drop_column('valuation_engine_version')
        batch_op.drop_column('reviewing_credit_officer')
        batch_op.drop_column('assigned_valuer')
        batch_op.drop_column('case_reference')

    with op.batch_alter_table('institutions') as batch_op:
        batch_op.drop_index('ix_institutions_agreement_status')
        batch_op.drop_index('ix_institutions_pilot_status')
        batch_op.drop_column('is_pilot_approved')
        batch_op.drop_column('approval_evidence_reference')
        batch_op.drop_column('approved_operational_scope')
        batch_op.drop_column('permitted_purposes')
        batch_op.drop_column('approved_data_categories')
        batch_op.drop_column('authorized_pilot_participants')
        batch_op.drop_column('pilot_expiry_date')
        batch_op.drop_column('pilot_commencement_date')
        batch_op.drop_column('pilot_authorization_status')
        batch_op.drop_column('dpa_signatory_name')
        batch_op.drop_column('dpa_signed_date')
        batch_op.drop_column('dpa_reference')
        batch_op.drop_column('dpa_status')
        batch_op.drop_column('agreement_evidence_url')
        batch_op.drop_column('agreement_signatory_title')
        batch_op.drop_column('agreement_signatory_name')
        batch_op.drop_column('agreement_signed_date')
        batch_op.drop_column('agreement_reference')
        batch_op.drop_column('agreement_status')
