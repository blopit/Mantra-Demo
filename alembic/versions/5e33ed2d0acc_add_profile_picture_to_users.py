"""add_profile_picture_to_users

Revision ID: 5e33ed2d0acc
Revises: 2d0ec431adca
Create Date: 2025-04-24 17:59:08.214446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e33ed2d0acc'
down_revision: Union[str, None] = '2d0ec431adca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add profile_picture column to users table."""
    op.add_column('users', sa.Column('profile_picture', sa.String))


def downgrade() -> None:
    """Remove profile_picture column from users table."""
    op.drop_column('users', 'profile_picture')
