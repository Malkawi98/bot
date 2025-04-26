"""Add coupons table

Revision ID: add_coupons_table
Revises: standalone_bot_settings
Create Date: 2025-04-26 18:55:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_coupons_table'
down_revision = 'standalone_bot_settings'  # Depends on the bot_settings migration
branch_labels = None
depends_on = None


def upgrade():
    # Check if coupons table already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'coupons' in inspector.get_table_names():
        print("coupons table already exists, skipping creation")
        return
        
    # Create coupons table
    op.create_table(
        'coupons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, index=True, unique=True),
        sa.Column('discount', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on id and code
    op.create_index('ix_coupons_id', 'coupons', ['id'], unique=False)
    op.create_index('ix_coupons_code', 'coupons', ['code'], unique=True)
    
    # Insert sample coupons
    op.execute(
        """
        INSERT INTO coupons (code, discount, description, is_active, expires_at)
        VALUES 
        ('WELCOME10', 10.0, 'Welcome discount for new customers', true, (CURRENT_TIMESTAMP + INTERVAL '30 days')),
        ('SUMMER25', 25.0, 'Summer sale discount', true, (CURRENT_TIMESTAMP + INTERVAL '60 days')),
        ('FREESHIP', 5.0, 'Free shipping coupon', true, (CURRENT_TIMESTAMP + INTERVAL '15 days'))
        """
    )


def downgrade():
    # Check if coupons table exists before dropping
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'coupons' in inspector.get_table_names():
        op.drop_index('ix_coupons_code')
        op.drop_index('ix_coupons_id')
        op.drop_table('coupons')
