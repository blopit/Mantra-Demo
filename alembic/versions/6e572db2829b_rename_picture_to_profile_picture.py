"""rename picture to profile_picture

Revision ID: 6e572db2829b
Revises: 328241a962f0
Create Date: 2024-05-03 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e572db2829b'
down_revision: Union[str, None] = '328241a962f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename picture column to profile_picture in users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('picture',
                            new_column_name='profile_picture',
                            existing_type=sa.String(),
                            existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Rename profile_picture column back to picture in users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('profile_picture',
                            new_column_name='picture',
                            existing_type=sa.String(),
                            existing_nullable=True)
