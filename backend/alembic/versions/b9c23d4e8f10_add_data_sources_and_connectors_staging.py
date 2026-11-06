"""add_data_sources_and_connectors_staging

Revision ID: b9c23d4e8f10
Revises: 79eb1b6cc667
Create Date: 2026-11-03 17:21:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9c23d4e8f10'
down_revision: Union[str, Sequence[str], None] = 'e14147f4c29a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include data_sources, ingestion_jobs, and raw_transaction_staging."""
    op.create_table(
        'data_sources',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source_code', sa.String(length=64), nullable=False),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('provider_name', sa.String(length=255), nullable=False),
        sa.Column('access_tier', sa.String(length=32), nullable=False),
        sa.Column('legal_authorization_basis', sa.Text(), nullable=False),
        sa.Column('api_base_url', sa.String(length=512), nullable=True),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('data_sources', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_data_sources_source_code'), ['source_code'], unique=True)

    op.create_table(
        'ingestion_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('trigger_mode', sa.String(length=32), nullable=False),
        sa.Column('cursor_state', sa.JSON(), nullable=True),
        sa.Column('records_fetched', sa.Integer(), nullable=False),
        sa.Column('records_staged', sa.Integer(), nullable=False),
        sa.Column('records_normalized', sa.Integer(), nullable=False),
        sa.Column('records_rejected', sa.Integer(), nullable=False),
        sa.Column('records_duplicate', sa.Integer(), nullable=False),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('audit_event_id', sa.String(length=36), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ingestion_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ingestion_jobs_source_id'), ['source_id'], unique=False)
        batch_op.create_index('ix_ingestion_jobs_source_status', ['source_id', 'status'], unique=False)
        batch_op.create_index(batch_op.f('ix_ingestion_jobs_started_at'), ['started_at'], unique=False)

    op.create_table(
        'raw_transaction_staging',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=False),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('payload_hash_sha256', sa.String(length=64), nullable=False),
        sa.Column('raw_payload', sa.JSON(), nullable=False),
        sa.Column('pii_scrub_status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['ingestion_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('raw_transaction_staging', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_raw_transaction_staging_job_id'), ['job_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_raw_transaction_staging_source_id'), ['source_id'], unique=False)
        batch_op.create_index('ix_raw_staging_job_row', ['job_id', 'row_index'], unique=False)
        batch_op.create_index('ix_raw_staging_payload_hash', ['payload_hash_sha256'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('raw_transaction_staging')
    op.drop_table('ingestion_jobs')
    op.drop_table('data_sources')
