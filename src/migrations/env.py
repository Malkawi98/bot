import asyncio
import importlib
import pkgutil
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.db.database import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Use PostgreSQL for all environments
# Check if we're running in a Docker container or locally
import os

try:
    # Try to use the settings from config
    db_url = settings.sqlalchemy_sync_url
    print(f"Using database URL from settings: {db_url}")
    
    # Check if we're running in Docker (this env var would be set in docker-compose)
    # Or use an environment variable to explicitly set the host
    explicit_host = os.environ.get('POSTGRES_SERVER')
    
    if explicit_host:
        # Use the explicitly provided host
        db_url = db_url.replace('localhost', explicit_host)
        db_url = db_url.replace('127.0.0.1', explicit_host)
        print(f"Using explicitly set database host: {explicit_host}")
        print(f"Updated database URL: {db_url}")
        
except Exception as e:
    # Fallback to hardcoded URL if settings fail
    print(f"Error getting database URL from settings: {e}")
    
    # Use localhost for local testing, db for Docker
    db_host = os.environ.get('POSTGRES_SERVER', 'localhost')
    db_url = f"postgresql://user:pass@{db_host}:5432/db"
    print(f"Using fallback database URL: {db_url}")

config.set_main_option(
    "sqlalchemy.url",
    db_url
)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# Auto-import all models in app.models
def import_models(package_name):
    package = importlib.import_module(package_name)
    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        importlib.import_module(module_name)

# Load all models dynamically
import_models("app.models")
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though an Engine is acceptable here as well.  By
    skipping the Engine creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_sync_migrations() -> None:
    """In this scenario we need to create an Engine and associate a connection with the context."""
    from sqlalchemy import engine_from_config, pool

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    run_sync_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
