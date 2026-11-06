"""add_governance_authorization_and_dataset_workflows

Revision ID: e2f34a5b6c7d
Revises: d8e90f12a345
Create Date: 2026-11-03 18:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f34a5b6c7d'
down_revision: Union[str, Sequence[str], None] = 'd8e90f12a345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include source authorization tracking and dataset approval governance."""
    # 1. Update data_sources table
    with op.batch_alter_table('data_sources', schema=None) as batch_op:
        batch_op.add_column(sa.Column('authorization_status', sa.String(length=32), nullable=False, server_default='AUTHORIZATION_PENDING'))
        batch_op.add_column(sa.Column('license_number', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('agreement_reference', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('permitted_purposes', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('retention_restrictions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('commercial_terms_summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('data_owner', sa.String(length=128), nullable=False, server_default='Institutional Data Officer'))
        batch_op.add_column(sa.Column('compliance_reviewer', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('status_updated_by', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('status_change_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('auth_secret_env_var', sa.String(length=128), nullable=False, server_default='ZAPKEY_API_KEY'))
        batch_op.create_index(batch_op.f('ix_data_sources_authorization_status'), ['authorization_status'], unique=False)

    # 2. Update datasets table
    with op.batch_alter_table('datasets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('approval_status', sa.String(length=32), nullable=False, server_default='DRAFT'))
        batch_op.add_column(sa.Column('data_owner', sa.String(length=128), nullable=False, server_default='Institutional Data Officer'))
        batch_op.add_column(sa.Column('responsible_reviewer', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('review_notes', sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f('ix_datasets_approval_status'), ['approval_status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('datasets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_datasets_approval_status'))
        batch_op.drop_column('review_notes')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('responsible_reviewer')
        batch_op.drop_column('data_owner')
        batch_op.drop_column('approval_status')

    with op.batch_alter_table('data_sources', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_data_sources_authorization_status'))
        batch_op.drop_column('auth_secret_env_var')
        batch_op.drop_column('status_change_reason')
        batch_op.drop_column('status_updated_by')
        batch_op.drop_column('compliance_reviewer')
        batch_op.drop_column('data_owner')
        batch_op.drop_column('commercial_terms_summary')
        batch_op.drop_column('retention_restrictions')
        batch_op.drop_column('permitted_purposes')
        batch_op.drop_column('valid_until')
        batch_op.drop_column('valid_from')
        batch_op.drop_column('agreement_reference')
        batch_op.drop_column('license_number')
        batch_op.drop_column('authorization_status')

