"""merge_multiple_heads

Revision ID: 732f7ec2f7b1
Revises: add_bot_settings_table, add_coupons_table
Create Date: 2025-04-27 03:45:44.435164

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '732f7ec2f7b1'
down_revision: Union[str, None] = ('add_bot_settings_table', 'add_coupons_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
