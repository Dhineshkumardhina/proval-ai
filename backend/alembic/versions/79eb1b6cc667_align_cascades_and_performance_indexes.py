"""align_cascades_and_performance_indexes

Revision ID: 79eb1b6cc667
Revises: e9731edc6e55
Create Date: 2026-11-02 21:48:17.519644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79eb1b6cc667'
down_revision: Union[str, Sequence[str], None] = 'e9731edc6e55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('ai_audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ai_audit_logs_created_at'), ['created_at'], unique=False)

    with op.batch_alter_table('audit_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_events_timestamp'), ['timestamp'], unique=False)

    with op.batch_alter_table('datasets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_datasets_file_hash_sha256'), ['file_hash_sha256'], unique=False)

    with op.batch_alter_table('valuation_cases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_valuation_cases_borrower_name'), ['borrower_name'], unique=False)
        batch_op.create_index(batch_op.f('ix_valuation_cases_created_at'), ['created_at'], unique=False)

    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    with op.batch_alter_table('valuation_results', schema=None, naming_convention=naming_convention) as batch_op:
        batch_op.drop_constraint('fk_valuation_results_case_id_valuation_cases', type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_valuation_results_case_id_valuation_cases',
            'valuation_cases',
            ['case_id'],
            ['id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    """Downgrade schema."""
    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    with op.batch_alter_table('valuation_results', schema=None, naming_convention=naming_convention) as batch_op:
        batch_op.drop_constraint('fk_valuation_results_case_id_valuation_cases', type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_valuation_results_case_id_valuation_cases',
            'valuation_cases',
            ['case_id'],
            ['id'],
            ondelete='SET NULL',
        )

    with op.batch_alter_table('valuation_cases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_valuation_cases_created_at'))
        batch_op.drop_index(batch_op.f('ix_valuation_cases_borrower_name'))

    with op.batch_alter_table('datasets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_datasets_file_hash_sha256'))

    with op.batch_alter_table('audit_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_events_timestamp'))

    with op.batch_alter_table('ai_audit_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ai_audit_logs_created_at'))
