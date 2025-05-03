"""add is_active to users

Revision ID: ebdfaa0c111f
Revises: 328241a962f0
Create Date: 2024-05-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ebdfaa0c111f'
down_revision: Union[str, None] = '328241a962f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_active column to users table with default value True
    op.add_column('users',
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove is_active column from users table
    op.drop_column('users', 'is_active')
