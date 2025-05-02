"""add n8n_workflow_id to mantra_installations

Revision ID: 34b17dec226e
Revises: 58ac25bd94fe
Create Date: 2024-03-19 12:34:56.789012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34b17dec226e'
down_revision: Union[str, None] = '58ac25bd94fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add n8n_workflow_id column to mantra_installations table
    op.add_column('mantra_installations', sa.Column('n8n_workflow_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove n8n_workflow_id column from mantra_installations table
    op.drop_column('mantra_installations', 'n8n_workflow_id')
