"""Change n8n_workflow_id to string

Revision ID: 0f095440e91b
Revises: 328241a962f0
Create Date: 2024-05-03 21:01:15.199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f095440e91b'
down_revision: Union[str, None] = '328241a962f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change n8n_workflow_id to string type
    with op.batch_alter_table('mantra_installations') as batch_op:
        batch_op.alter_column('n8n_workflow_id',
                            existing_type=sa.Integer(),
                            type_=sa.String(),
                            existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Change n8n_workflow_id back to integer type
    with op.batch_alter_table('mantra_installations') as batch_op:
        batch_op.alter_column('n8n_workflow_id',
                            existing_type=sa.String(),
                            type_=sa.Integer(),
                            existing_nullable=True)
