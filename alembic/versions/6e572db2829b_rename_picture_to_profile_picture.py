"""rename_picture_to_profile_picture

Revision ID: 6e572db2829b
Revises: ebdfaa0c111f
Create Date: 2024-05-03 14:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6e572db2829b'
down_revision = 'ebdfaa0c111f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename picture column to profile_picture
    op.alter_column('users', 'picture',
                    new_column_name='profile_picture',
                    existing_type=sa.String(),
                    existing_nullable=True)


def downgrade() -> None:
    # Rename profile_picture column back to picture
    op.alter_column('users', 'profile_picture',
                    new_column_name='picture',
                    existing_type=sa.String(),
                    existing_nullable=True)
