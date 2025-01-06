"""add activity levels

Revision ID: 016e3ac0eeb9
Revises: ae99c9eade9b
Create Date: 2025-01-05 01:55:35.359059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '016e3ac0eeb9'
down_revision: Union[str, None] = 'ae99c9eade9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print(f"running upgrade for revision {revision}")

    activity_levels_table = op.create_table('activity_levels',
        sa.Column('id', mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('name', mysql.VARCHAR(length=100), nullable=False),
        sa.Column('description', mysql.VARCHAR(length=5000), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_activity_levels')),
        sa.UniqueConstraint('name', name=op.f('uq_activity_levels_name'))
    )
    insert_activity_levels = mysql.insert(activity_levels_table).values(
        [
            {"id": 1, "name": "LITTLE_TO_NO",
             "description": "Little to no exercise"},
            {"id": 2, "name": "MODERATE_1_3_PER_WEEK",
             "description": "Light exercise, 1-3 times per week"},
            {"id": 3, "name": "HIGH_3_5_PER_WEEK",
             "description": "Moderate exercise, 3-5 times per week"},
            {"id": 4, "name": "VERY_HIGH_6_7_PER_WEEK",
             "description": "Intense exercise, 6-7 times per week"},
            {"id": 5, "name": "HYPERACTIVE_2_HOURS_PER_DAY",
             "description": "Very intense, 2 hours per day or more"}
        ]
    )
    upsert_activity_levels = insert_activity_levels.on_duplicate_key_update(
        name=insert_activity_levels.inserted.name,
        description=insert_activity_levels.inserted.description
    )
    op.execute(upsert_activity_levels)

    op.add_column('users', sa.Column('activity_level_id', mysql.INTEGER(unsigned=True), nullable=False, server_default="1"))
    op.create_foreign_key(op.f('fk_users_activity_level_id_activity_levels'), 'users', 'activity_levels', ['activity_level_id'], ['id'])
    op.alter_column(
        "users",
        column_name="activity_level_id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        server_default=None
    )



def downgrade() -> None:
    print(f"running downgrade for revision {revision}")
    op.drop_constraint(op.f('fk_users_activity_level_id_activity_levels'), 'users', type_='foreignkey')
    op.drop_column('users', 'activity_level_id')
    op.drop_table('activity_levels')
