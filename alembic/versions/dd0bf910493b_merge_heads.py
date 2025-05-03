"""merge_heads

Revision ID: dd0bf910493b
Revises: 6e572db2829b, 872c44ba33d7
Create Date: 2025-05-03 18:16:07.101658

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd0bf910493b'
down_revision: Union[str, None] = ('6e572db2829b', '872c44ba33d7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
