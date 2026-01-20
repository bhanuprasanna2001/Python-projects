"""
Alembic Environment Configuration
=================================
This file configures how Alembic connects to the database
and generates migrations.
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import your models' Base
from models import Base
from database import DATABASE_URL

# Alembic Config object
config = context.config

# Set the database URL programmatically (overrides alembic.ini)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This generates SQL scripts without connecting to the database.
    Good for reviewing changes before applying.
    
    Usage: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include object names in autogenerate
        include_object=include_object,
        # Compare types for column changes
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    Creates an Engine and connects to the database to run migrations.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Include object names in autogenerate
            include_object=include_object,
            # Compare types for column changes
            compare_type=True,
            # Compare server defaults
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects for autogenerate.
    
    Use this to include/exclude specific tables or objects.
    """
    # Exclude specific tables if needed
    excluded_tables = ['alembic_version', 'spatial_ref_sys']
    
    if type_ == "table" and name in excluded_tables:
        return False
    
    return True


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
