# Alembic Commands Cheat Sheet

## Initial Setup

```bash
# Initialize Alembic in project
alembic init alembic

# This creates:
# - alembic.ini (configuration)
# - alembic/ directory with env.py and versions/
```

## Creating Migrations

```bash
# Auto-generate from model changes (RECOMMENDED)
alembic revision --autogenerate -m "Add users table"

# Create empty migration (for manual edits)
alembic revision -m "Custom migration"
```

## Running Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade abc123

# Upgrade by N revisions
alembic upgrade +2

# Downgrade by 1 revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade abc123

# Downgrade to nothing (empty database)
alembic downgrade base
```

## Viewing Status

```bash
# Current revision
alembic current

# Migration history
alembic history

# Show verbose history
alembic history --verbose

# Show pending migrations
alembic history --indicate-current
```

## Useful Commands

```bash
# Show SQL without executing (for review)
alembic upgrade head --sql

# Stamp database (mark as upgraded without running)
alembic stamp head

# Show branches (if any)
alembic branches

# Merge branches
alembic merge -m "merge branches" rev1 rev2
```

## Common Patterns

### Safe Migration Example

```python
def upgrade():
    # Create table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Add index
    op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade():
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
```

### Add Column with Default

```python
def upgrade():
    op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default='true'))


def downgrade():
    op.drop_column('users', 'is_active')
```

### Data Migration

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

def upgrade():
    # Define table reference
    users = table('users',
        column('id', sa.Integer),
        column('full_name', sa.String),
        column('first_name', sa.String),
        column('last_name', sa.String)
    )
    
    # Update data
    op.execute(
        users.update()
        .where(users.c.full_name == None)
        .values(full_name=users.c.first_name + ' ' + users.c.last_name)
    )
```

### Batch Operations (SQLite)

```python
def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('age', sa.Integer()))
        batch_op.drop_column('old_column')
```
