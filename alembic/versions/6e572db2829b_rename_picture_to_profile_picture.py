"""rename_picture_to_profile_picture

Revision ID: 6e572db2829b
Revises: ebdfaa0c111f
Create Date: 2025-05-03 14:04:01.820316

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e572db2829b'
down_revision: Union[str, None] = 'ebdfaa0c111f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
