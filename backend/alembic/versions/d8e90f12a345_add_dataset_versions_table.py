"""add_dataset_versions_table

Revision ID: d8e90f12a345
Revises: c7d89e01f234
Create Date: 2026-11-03 17:43:55.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8e90f12a345'
down_revision: Union[str, Sequence[str], None] = 'c7d89e01f234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include dataset_versions."""
    op.create_table(
        'dataset_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('dataset_id', sa.String(length=36), nullable=False),
        sa.Column('semver_tag', sa.String(length=32), nullable=False),
        sa.Column('version_title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('total_records', sa.Integer(), nullable=False),
        sa.Column('verified_records', sa.Integer(), nullable=False),
        sa.Column('rejected_records', sa.Integer(), nullable=False),
        sa.Column('duplicate_records', sa.Integer(), nullable=False),
        sa.Column('quarantined_records', sa.Integer(), nullable=False),
        sa.Column('dataset_checksum_sha256', sa.String(length=64), nullable=False),
        sa.Column('geographic_distribution', sa.JSON(), nullable=False),
        sa.Column('property_type_distribution', sa.JSON(), nullable=False),
        sa.Column('source_distribution', sa.JSON(), nullable=False),
        sa.Column('validation_summary', sa.JSON(), nullable=False),
        sa.Column('included_transaction_ids', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(length=128), nullable=False),
        sa.Column('approval_status', sa.String(length=32), nullable=False),
        sa.Column('approved_by', sa.String(length=128), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_ml_eligible', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('dataset_versions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_dataset_versions_dataset_id'), ['dataset_id'], unique=False)
        batch_op.create_index('ix_dataset_versions_dataset_semver', ['dataset_id', 'semver_tag'], unique=True)
        batch_op.create_index(batch_op.f('ix_dataset_versions_created_at'), ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('dataset_versions')

