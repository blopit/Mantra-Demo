"""add_google_account_id_to_google_integrations

Revision ID: 872c44ba33d7
Revises: 6e572db2829b
Create Date: 2025-05-03 18:15:43.776938

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '872c44ba33d7'
down_revision: Union[str, None] = '6e572db2829b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
