"""add_quarantined_records_and_verification_evidence

Revision ID: c7d89e01f234
Revises: b9c23d4e8f10
Create Date: 2026-11-03 17:39:40.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d89e01f234'
down_revision: Union[str, Sequence[str], None] = 'b9c23d4e8f10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include quarantined_records and verification_evidence."""
    op.create_table(
        'quarantined_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('dataset_id', sa.String(length=36), nullable=False),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('quarantine_code', sa.String(length=64), nullable=False),
        sa.Column('quarantine_reason', sa.String(length=500), nullable=False),
        sa.Column('anomaly_score', sa.Float(), nullable=False),
        sa.Column('anomalous_fields', sa.JSON(), nullable=False),
        sa.Column('raw_payload', sa.JSON(), nullable=False),
        sa.Column('resolution_status', sa.String(length=32), nullable=False),
        sa.Column('reviewed_by', sa.String(length=128), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('quarantined_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_quarantined_records_dataset_id'), ['dataset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_quarantined_records_quarantine_code'), ['quarantine_code'], unique=False)
        batch_op.create_index('ix_quarantined_records_dataset_code', ['dataset_id', 'quarantine_code'], unique=False)

    op.create_table(
        'verification_evidence',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('transaction_id', sa.String(length=36), nullable=False),
        sa.Column('verification_status', sa.String(length=32), nullable=False),
        sa.Column('verifier_id', sa.String(length=128), nullable=False),
        sa.Column('verifier_method', sa.String(length=64), nullable=False),
        sa.Column('source_origin', sa.String(length=128), nullable=False),
        sa.Column('source_document_ref', sa.String(length=255), nullable=False),
        sa.Column('original_record_hash', sa.String(length=64), nullable=False),
        sa.Column('normalized_record_hash', sa.String(length=64), nullable=False),
        sa.Column('dataset_version', sa.String(length=32), nullable=True),
        sa.Column('verification_evidence_details', sa.JSON(), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['imported_transactions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('verification_evidence', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_verification_evidence_transaction_id'), ['transaction_id'], unique=False)
        batch_op.create_index('ix_verification_evidence_tx_id', ['transaction_id'], unique=False)
        batch_op.create_index('ix_verification_evidence_status', ['verification_status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('verification_evidence')
    op.drop_table('quarantined_records')

