"""Create bot_settings table (standalone)

Revision ID: standalone_bot_settings
Revises: add_products_table
Create Date: 2025-04-26 18:50:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'standalone_bot_settings'
down_revision = None  # No dependency on previous migrations
branch_labels = None
depends_on = None


def upgrade():
    # Check if bot_settings table already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'bot_settings' not in inspector.get_table_names():
        print("Creating bot_settings table...")
        # Create bot_settings table
        op.create_table(
            'bot_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('bot_name', sa.String(255), nullable=False, server_default='E-Commerce Support Bot'),
            sa.Column('welcome_message', sa.Text(), nullable=False, 
                     server_default='Hello! I\'m your support assistant. How can I help you today?'),
            sa.Column('fallback_message', sa.Text(), nullable=False, 
                     server_default='I\'m sorry, I couldn\'t understand your request. Could you please rephrase or select one of the quick options below?'),
            sa.Column('quick_actions', sa.JSON(), nullable=True),
            sa.Column('advanced_settings', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create index on id
        op.create_index('ix_bot_settings_id', 'bot_settings', ['id'], unique=False)
        
        # Insert default bot settings
        op.execute(
            """
            INSERT INTO bot_settings (bot_name, welcome_message, fallback_message, quick_actions)
            VALUES (
                'E-Commerce Support Bot',
                'Hello! I''m your support assistant. How can I help you today?',
                'I''m sorry, I couldn''t understand your request. Could you please rephrase or select one of the quick options below?',
                '["Check Order Status", "Browse Products", "Contact Support"]'
            )
            """
        )
    else:
        print("bot_settings table already exists, skipping creation")


def downgrade():
    # Check if bot_settings table exists before dropping
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'bot_settings' in inspector.get_table_names():
        op.drop_index('ix_bot_settings_id')
        op.drop_table('bot_settings')
