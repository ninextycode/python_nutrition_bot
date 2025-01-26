"""Add birthday congratulated column

Revision ID: 0238f7423a3a
Revises: d50ed91109e2
Create Date: 2025-01-23 22:33:52.888233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '0238f7423a3a'
down_revision: Union[str, None] = 'd50ed91109e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print(f"running upgrade for revision {revision}")
    op.add_column('users', sa.Column('last_birthday_congratulated', mysql.YEAR(), nullable=True))


def downgrade() -> None:
    print(f"running downgrade for revision {revision}")
    op.drop_column('users', 'last_birthday_congratulated')
