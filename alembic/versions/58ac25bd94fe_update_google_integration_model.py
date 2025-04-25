"""update_google_integration_model

Revision ID: 58ac25bd94fe
Revises: 5e33ed2d0acc
Create Date: 2025-04-25 15:19:54.132869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '58ac25bd94fe'
down_revision: Union[str, None] = '5e33ed2d0acc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create a new table with the updated schema
    with op.batch_alter_table('google_integrations', schema=None) as batch_op:
        # Add new columns
        batch_op.add_column(sa.Column('google_account_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('email', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(), nullable=False, server_default='pending'))
        batch_op.add_column(sa.Column('access_token', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('refresh_token', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('disconnected_at', sa.DateTime(), nullable=True))
        
        # Alter id column type to UUID
        batch_op.alter_column('id',
            type_=sa.String(),  # Using String for UUID in SQLite
            existing_type=sa.Integer(),
            nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('google_integrations', schema=None) as batch_op:
        # Remove new columns
        batch_op.drop_column('disconnected_at')
        batch_op.drop_column('expires_at')
        batch_op.drop_column('refresh_token')
        batch_op.drop_column('access_token')
        batch_op.drop_column('status')
        batch_op.drop_column('email')
        batch_op.drop_column('google_account_id')
        
        # Change id column back to integer
        batch_op.alter_column('id',
            type_=sa.Integer(),
            existing_type=sa.String(),  # Using String for UUID in SQLite
            nullable=False)
