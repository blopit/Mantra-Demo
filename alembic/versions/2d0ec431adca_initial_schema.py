"""initial_schema

Revision ID: 2d0ec431adca
Revises: 
Create Date: 2025-04-24 17:45:41.213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import String, Column, ForeignKey, DateTime, Boolean, JSON, Integer, Float, Text


# revision identifiers, used by Alembic.
revision: str = '2d0ec431adca'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table first since other tables reference it
    op.create_table('users',
        sa.Column('id', String, primary_key=True),
        sa.Column('email', String, unique=True, nullable=False),
        sa.Column('name', String),
        sa.Column('is_active', Boolean, nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', DateTime(timezone=True))
    )

    # Create mantras table
    op.create_table('mantras',
        sa.Column('id', String, primary_key=True),
        sa.Column('name', String, nullable=False),
        sa.Column('description', String),
        sa.Column('workflow_json', JSON, nullable=False),
        sa.Column('created_at', DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', DateTime(timezone=True)),
        sa.Column('is_active', Boolean, server_default=sa.text('1')),
        sa.Column('user_id', String, ForeignKey('users.id')),
    )

    # Create mantra_installations table
    op.create_table('mantra_installations',
        sa.Column('id', String, primary_key=True),
        sa.Column('mantra_id', String, ForeignKey('mantras.id'), nullable=False),
        sa.Column('user_id', String, ForeignKey('users.id'), nullable=False),
        sa.Column('installed_at', DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('status', String, server_default='active'),
        sa.Column('config', JSON)
    )

    # Create google_auth table
    op.create_table('google_auth',
        sa.Column('id', Integer, primary_key=True),
        sa.Column('user_id', String, ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('email', String, nullable=False),
        sa.Column('access_token', Text),
        sa.Column('refresh_token', Text),
        sa.Column('token_expiry', DateTime(timezone=True)),
        sa.Column('created_at', DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', DateTime(timezone=True))
    )

    # Create google_integrations table
    op.create_table('google_integrations',
        sa.Column('id', Integer, primary_key=True),
        sa.Column('user_id', String, ForeignKey('users.id'), nullable=False),
        sa.Column('service_name', String, nullable=False),
        sa.Column('is_active', Boolean, server_default=sa.text('1')),
        sa.Column('scopes', String),
        sa.Column('settings', String),
        sa.Column('created_at', DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', DateTime(timezone=True))
    )

    # Create contacts table
    op.create_table('contacts',
        sa.Column('id', Integer, primary_key=True),
        sa.Column('user_id', String, ForeignKey('users.id'), nullable=False),
        sa.Column('email', String, nullable=False),
        sa.Column('name', String),
        sa.Column('source', String, nullable=False),
        sa.Column('external_id', String),
        sa.Column('created_at', DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', DateTime(timezone=True)),
        sa.Column('avatar', String(255)),
        sa.Column('apps', JSON),
        sa.Column('ai_engagement_score', Float),
        sa.Column('preferred_contact_method', String(50)),
        sa.Column('last_interaction', DateTime(timezone=True)),
        sa.Column('location', String(100)),
        sa.Column('mood', String(50)),
        sa.Column('achievements', JSON),
        sa.Column('communication_preferences', JSON),
        sa.Column('relationships', JSON),
        sa.Column('stats', JSON),
        sa.Column('tags', JSON),
        sa.Column('custom_fields', JSON),
        sa.Column('availability', JSON),
        sa.Column('summary', Text),
        sa.Column('interests', JSON),
        sa.Column('notes', Text),
        sa.Column('relationship_summary', Text),
        sa.Column('communication_style', String(50)),
        sa.Column('birthday', String(20))
    )


def downgrade() -> None:
    op.drop_table('contacts')
    op.drop_table('google_integrations')
    op.drop_table('google_auth')
    op.drop_table('mantra_installations')
    op.drop_table('mantras')
    op.drop_table('users')
