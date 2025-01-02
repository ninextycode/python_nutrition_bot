"""autoincrement id

Revision ID: 3325dbd1fa8b
Revises: 0e8298edf774
Create Date: 2024-12-25 20:38:47.235523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '3325dbd1fa8b'
down_revision: Union[str, None] = '0e8298edf774'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# cannot add autoincrement without it
def drop_fk_constraints():
    op.drop_constraint(op.f('fk_users_targets_user_id_users'), 'users_targets', type_='foreignkey')
    op.drop_constraint(op.f('fk_users_goal_id_goals'), 'users', type_='foreignkey')
    op.drop_constraint(op.f('fk_users_timezone_id_timezones'), 'users', type_='foreignkey')
    op.drop_constraint(op.f('fk_users_gender_id_genders'), 'users', type_='foreignkey')
    op.drop_constraint(op.f('fk_meals_for_future_use_user_id_users'), 'meals_for_future_use', type_='foreignkey')
    op.drop_constraint(op.f('fk_meals_eaten_user_id_users'), 'meals_eaten', type_='foreignkey')


def add_fk_constraints():
    op.create_foreign_key(op.f('fk_meals_eaten_user_id_users'), 'meals_eaten', 'users', ['user_id'], ['id'])
    op.create_foreign_key(
        op.f('fk_meals_for_future_use_user_id_users'), 'meals_for_future_use', 'users', ['user_id'], ['id']
    )
    op.create_foreign_key(op.f('fk_users_gender_id_genders'), 'users', 'genders', ['gender_id'], ['id'])
    op.create_foreign_key(op.f('fk_users_timezone_id_timezones'), 'users', 'timezones', ['timezone_id'], ['id'])
    op.create_foreign_key(op.f('fk_users_goal_id_goals'), 'users', 'goals', ['goal_id'], ['id'])
    op.create_foreign_key(op.f('fk_users_targets_user_id_users'), 'users_targets', 'users', ['user_id'], ['id'])


def upgrade() -> None:
    print(f"running upgrade for revision {revision}")

    drop_fk_constraints()

    op.alter_column(
        "genders",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=True
    )
    op.alter_column(
        "goals",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=True
    )
    op.alter_column(
        "timezones",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=True
    )
    op.alter_column(
        "users",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=True
    )
    op.alter_column(
        "meals_eaten",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=True
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=True
    )
    op.alter_column(
        "users_targets",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=True
    )

    add_fk_constraints()


def downgrade() -> None:
    print(f"running downgrade for revision {revision}")
    drop_fk_constraints()
    op.alter_column(
        "genders",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=False
    )
    op.alter_column(
        "goals",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=False
    )
    op.alter_column(
        "timezones",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=False
    )
    op.alter_column(
        "users",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=False
    )
    op.alter_column(
        "users_targets",
        column_name="id",
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False,
        autoincrement=False
    )
    add_fk_constraints()
