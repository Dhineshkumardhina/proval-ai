"""phase4c_data_acquisition_schema_updates

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-11-05 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with built_up_area_sqft in imported_transactions and source_category in data_sources."""
    # 1. Update imported_transactions table
    with op.batch_alter_table('imported_transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('built_up_area_sqft', sa.Float(), nullable=True))

    # 2. Update data_sources table
    with op.batch_alter_table('data_sources', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_category', sa.String(length=64), nullable=True, server_default='LICENSED_PROVIDER'))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('data_sources', schema=None) as batch_op:
        batch_op.drop_column('source_category')

    with op.batch_alter_table('imported_transactions', schema=None) as batch_op:
        batch_op.drop_column('built_up_area_sqft')

