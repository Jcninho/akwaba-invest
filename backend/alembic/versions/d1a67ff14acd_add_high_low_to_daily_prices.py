"""add_high_low_to_daily_prices

Revision ID: d1a67ff14acd
Revises: d3afda8ba7a6
Create Date: 2026-05-21 19:20:28.468840

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd1a67ff14acd'
down_revision: Union[str, None] = 'd3afda8ba7a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('daily_prices',
        sa.Column('high_price', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('daily_prices',
        sa.Column('low_price', sa.Numeric(precision=12, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column('daily_prices', 'low_price')
    op.drop_column('daily_prices', 'high_price')
