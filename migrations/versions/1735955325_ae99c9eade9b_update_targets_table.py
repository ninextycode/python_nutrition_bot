"""Update targets table

Revision ID: ae99c9eade9b
Revises: 3325dbd1fa8b
Create Date: 2025-01-04 01:48:45.896883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'ae99c9eade9b'
down_revision: Union[str, None] = '3325dbd1fa8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print(f"running upgrade for revision {revision}")
    op.add_column('users_targets', sa.Column('target_type', mysql.ENUM('MAXIMUM', 'MINIMUM'), nullable=False))


def downgrade() -> None:
    print(f"running downgrade for revision {revision}")
    op.drop_column('users_targets', 'target_type')

