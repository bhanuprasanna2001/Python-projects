"""Add avatar_url to users and seed initial roles

Revision ID: 002_add_avatar_and_roles
Revises: 001_initial
Create Date: 2024-01-02 00:00:00.000000

This migration demonstrates:
- Adding a new column
- Data migration (seeding roles)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision: str = '002_add_avatar_and_roles'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add avatar_url column and seed roles."""
    
    # Add new column to users
    op.add_column(
        'users',
        sa.Column('avatar_url', sa.String(500), nullable=True)
    )
    
    # Data migration: Seed initial roles
    # Define table structure for raw SQL operations
    roles = table('roles',
        column('id', sa.Integer),
        column('name', sa.String),
        column('description', sa.String)
    )
    
    # Insert seed data
    op.bulk_insert(roles, [
        {'id': 1, 'name': 'admin', 'description': 'Administrator with full access'},
        {'id': 2, 'name': 'editor', 'description': 'Can create and edit content'},
        {'id': 3, 'name': 'viewer', 'description': 'Read-only access'},
    ])


def downgrade() -> None:
    """Remove avatar_url column and seeded roles."""
    
    # Remove seeded roles
    op.execute("DELETE FROM roles WHERE name IN ('admin', 'editor', 'viewer')")
    
    # Remove column
    op.drop_column('users', 'avatar_url')
