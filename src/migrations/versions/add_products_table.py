"""Add products table

Revision ID: add_products_table
Revises: 
Create Date: 2025-04-26 03:15:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_products_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Check if products table already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'products' not in inspector.get_table_names():
        print("Creating products table...")
        op.create_table(
            'products',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(255), nullable=False, index=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('price', sa.Float(), nullable=False),
            sa.Column('currency', sa.String(3), server_default='USD'),
            sa.Column('stock_quantity', sa.Integer(), server_default='0'),
            sa.Column('image_url', sa.String(255), nullable=True),
            sa.Column('category', sa.String(100), nullable=True, index=True),
            sa.Column('is_active', sa.Boolean(), server_default='true'),
            sa.Column('created_at', sa.String(), server_default=sa.text("(datetime('now'))")),
            sa.Column('updated_at', sa.String(), server_default=sa.text("(datetime('now'))")),
            sa.Column('language', sa.String(10), server_default='en'),
            sa.Column('alternative_to_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['alternative_to_id'], ['products.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index('ix_products_id', 'products', ['id'], unique=False)
        op.create_index('ix_products_name', 'products', ['name'], unique=False)
        op.create_index('ix_products_category', 'products', ['category'], unique=False)
    else:
        print("products table already exists, skipping creation")


def downgrade():
    op.drop_index('ix_products_category')
    op.drop_index('ix_products_name')
    op.drop_index('ix_products_id')
    op.drop_table('products')
