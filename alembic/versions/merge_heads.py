"""merge heads

Revision ID: merge_heads
Revises: 0f095440e91b, dd0bf910493b
Create Date: 2024-05-03 21:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('0f095440e91b', 'dd0bf910493b')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass 