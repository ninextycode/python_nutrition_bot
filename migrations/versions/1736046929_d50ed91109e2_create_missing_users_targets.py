"""create missing users_targets

Revision ID: d50ed91109e2
Revises: 016e3ac0eeb9
Create Date: 2025-01-05 03:15:29.681891

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'd50ed91109e2'
down_revision: Union[str, None] = '016e3ac0eeb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print(f"running upgrade for revision {revision}")

    connection = op.get_bind()
    metadata = sa.MetaData()

    # Reflect the existing tables
    users_table = sa.Table('users', metadata, autoload_with=connection)
    users_targets_table = sa.Table('users_targets', metadata, autoload_with=connection)

    # Fetch all users
    users = connection.execute(sa.select(users_table.c.id)).fetchall()

    for user in users:
        user_id = user.id

        # Check if a UserTarget already exists for this user
        user_target = connection.execute(
            sa.select(users_targets_table.c.id).where(users_targets_table.c.user_id == user_id)
        ).fetchone()

        if user_target is None:
            # Insert default UserTarget
            connection.execute(
                sa.insert(users_targets_table).values(
                    user_id=user_id,
                    calories=0, protein=0, fat=0, carbs=0, target_type='MINIMUM'
                )
            )


def downgrade() -> None:
    print(f"running downgrade for revision {revision}")
