"""phase4b7_remediation_schema_updates

Revision ID: f3a4b5c6d7e8
Revises: e2f34a5b6c7d
Create Date: 2026-11-05 19:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, Sequence[str], None] = 'e2f34a5b6c7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with cadastral identifiers, spatial indexing, erasure tracking, and Merkle audit anchors."""
    # 1. Update imported_transactions table
    with op.batch_alter_table('imported_transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('original_latitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('original_longitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('precision_digits', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('survey_number', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('village_name', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('taluka_tehsil', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('sro_jurisdiction_code', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('cadastral_parcel_id', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('spatial_accuracy_tier', sa.String(length=32), nullable=True, server_default='COORDINATE_BOUNDED'))
        batch_op.create_index(batch_op.f('ix_imported_tx_lat_lon'), ['latitude', 'longitude'], unique=False)
        batch_op.create_index(batch_op.f('ix_imported_transactions_survey_number'), ['survey_number'], unique=False)
        batch_op.create_index(batch_op.f('ix_imported_transactions_village_name'), ['village_name'], unique=False)
        batch_op.create_index(batch_op.f('ix_imported_transactions_sro_jurisdiction_code'), ['sro_jurisdiction_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_imported_transactions_cadastral_parcel_id'), ['cadastral_parcel_id'], unique=False)

    # 2. Create erasure_requests table
    op.create_table(
        'erasure_requests',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('transaction_id', sa.String(length=64), nullable=False),
        sa.Column('dataset_id', sa.String(length=64), nullable=True),
        sa.Column('requester_id', sa.String(length=64), nullable=False),
        sa.Column('requester_role', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('records_erased_summary', sa.JSON(), nullable=True),
        sa.Column('legal_backup_disclaimer', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    with op.batch_alter_table('erasure_requests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_erasure_requests_transaction_id'), ['transaction_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_erasure_requests_dataset_id'), ['dataset_id'], unique=False)

    # 3. Create audit_merkle_epochs table
    op.create_table(
        'audit_merkle_epochs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('epoch_number', sa.Integer(), nullable=False),
        sa.Column('merkle_root_hash', sa.String(length=64), nullable=False),
        sa.Column('start_sequence', sa.Integer(), nullable=False),
        sa.Column('end_sequence', sa.Integer(), nullable=False),
        sa.Column('event_count', sa.Integer(), nullable=False),
        sa.Column('anchor_manifest', sa.Text(), nullable=False),
        sa.Column('anchor_token', sa.Text(), nullable=True),
        sa.Column('anchored_by', sa.String(length=64), nullable=False, server_default='SYSTEM_ANCHOR'),
        sa.Column('anchored_at', sa.DateTime(), nullable=False),
    )
    with op.batch_alter_table('audit_merkle_epochs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_merkle_epochs_epoch_number'), ['epoch_number'], unique=True)

    # 4. Remove duplicate index on verification_evidence
    try:
        with op.batch_alter_table('verification_evidence', schema=None) as batch_op:
            batch_op.drop_index('ix_verification_evidence_tx_id')
    except Exception:
        pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('audit_merkle_epochs')
    op.drop_table('erasure_requests')
    with op.batch_alter_table('imported_transactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_imported_transactions_cadastral_parcel_id'))
        batch_op.drop_index(batch_op.f('ix_imported_transactions_survey_number'))
        batch_op.drop_index(batch_op.f('ix_imported_tx_lat_lon'))
        batch_op.drop_column('spatial_accuracy_tier')
        batch_op.drop_column('cadastral_parcel_id')
        batch_op.drop_column('sro_jurisdiction_code')
        batch_op.drop_column('taluka_tehsil')
        batch_op.drop_column('village_name')
        batch_op.drop_column('survey_number')
        batch_op.drop_column('precision_digits')
        batch_op.drop_column('original_longitude')
        batch_op.drop_column('original_latitude')
