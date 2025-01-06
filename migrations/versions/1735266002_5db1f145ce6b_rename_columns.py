"""rename columns, drop default utc time assignment

Revision ID: 5db1f145ce6b
Revises: 8c64364824aa
Create Date: 2024-12-22 01:37:29.609484

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "5db1f145ce6b"
down_revision: Union[str, None] = "8c64364824aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print(f"running upgrade for revision {revision}")

    op.drop_constraint(
        table_name="users", type_="foreignkey",
        constraint_name="users_ibfk_1"
    )
    op.drop_constraint(
        table_name="users", type_="foreignkey",
        constraint_name="users_ibfk_2"
    )
    op.drop_constraint(
        table_name="users", type_="foreignkey",
        constraint_name="users_ibfk_3"
    )
    op.drop_constraint(
        table_name="meals_eaten", type_="foreignkey",
        constraint_name="meals_eaten_ibfk_1"
    )
    op.drop_constraint(
        table_name="meals_for_future_use", type_="foreignkey",
        constraint_name="meals_for_future_use_ibfk_1"
    )
    op.drop_constraint(
        table_name="users_targets", type_="foreignkey",
        constraint_name="users_targets_ibfk_1"
    )
    op.drop_constraint(
        table_name="users", type_="check",
        constraint_name=op.f("ck_users_users_chk_1")
    )

    op.drop_index('Gender', table_name='genders')
    op.drop_index('Goal', table_name='goals')
    op.drop_index('UserID', table_name='meals_eaten')
    op.drop_index('UserID', table_name='meals_for_future_use')
    op.drop_index('TimeZone', table_name='timezones')
    op.drop_index('GenderID', table_name='users')
    op.drop_index('GoalID', table_name='users')
    op.drop_index('TelegramID', table_name='users')
    op.drop_index('TimeZoneID', table_name='users')
    op.drop_index('UserID', table_name='users_targets')

    op.alter_column(
        "timezones",
        column_name="ID", new_column_name="id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "timezones",
        column_name="TimeZone", new_column_name="timezone",
        existing_type=sa.String(length=200), type_=mysql.VARCHAR(length=200),
        existing_nullable=False
    )

    op.alter_column(
        "genders",
        column_name="ID", new_column_name="id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "genders",
        column_name="Gender", new_column_name="gender",
        existing_type=sa.String(length=50), type_=mysql.VARCHAR(length=50),
        existing_nullable=False
    )

    op.alter_column(
        "goals",
        column_name="ID", new_column_name="id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "goals",
        column_name="Goal", new_column_name="goal",
        existing_type=sa.String(length=200), type_=mysql.VARCHAR(length=200),
        existing_nullable=False
    )

    op.alter_column(
        "meals_eaten",
        column_name="ID", new_column_name="id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )

    op.alter_column(
        "meals_eaten",
        column_name="UserID", new_column_name="user_id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="CreatedUTCDateTime", new_column_name="created_utc_datetime",
        existing_type=sa.DateTime(), type_=mysql.DATETIME(),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="CreatedLocalDateTime", new_column_name="created_local_datetime",
        existing_type=sa.DateTime(), type_=mysql.DATETIME(),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="Name", new_column_name="name",
        existing_type=sa.String(length=100), type_=mysql.VARCHAR(length=100),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="Weight", new_column_name="weight",
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="Calories", new_column_name="calories",
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="Carbs", new_column_name="carbs",
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="Protein", new_column_name="protein",
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="Fat", new_column_name="fat",
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="Description", new_column_name="description",
        existing_type=sa.String(length=5000), type_=mysql.VARCHAR(length=5000),
        existing_nullable=True
    )

    op.alter_column(
        "meals_for_future_use",
        column_name="ID", new_column_name="id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="UserID", new_column_name="user_id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="CreatedUTCDateTime", new_column_name="created_utc_datetime",
        existing_type=sa.DateTime(), type_=mysql.DATETIME(),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="Name", new_column_name="name",
        existing_type=sa.String(length=100), type_=mysql.VARCHAR(length=100),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="DefaultWeightGrams", new_column_name="default_weight_grams",
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="CaloriesPer100g", new_column_name="calories_per_100g",
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="ProteinPer100g", new_column_name="protein_per_100g",
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="FatPer100g", new_column_name="fat_per_100g",
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="CarbsPer100g", new_column_name="carbs_per_100g",
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="Description", new_column_name="description",
        type_=mysql.VARCHAR(length=5000),
        existing_type=sa.String(length=5000),
        existing_nullable=True
    )

    op.alter_column(
        "users",
        column_name="ID", new_column_name="id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="CreatedUTCDateTime", new_column_name="created_utc_datetime",
        existing_type=sa.DateTime(), type_=mysql.DATETIME(),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="Name", new_column_name="name",
        existing_type=sa.String(length=100), type_=mysql.VARCHAR(length=100),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="TelegramID", new_column_name="telegram_id",
        existing_type=sa.String(length=100), type_=mysql.VARCHAR(length=100),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="IsActive", new_column_name="is_activated",
        existing_type=mysql.TINYINT(display_width=1), type_=mysql.BOOLEAN(),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="TimeZoneID", new_column_name="timezone_id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="GenderID", new_column_name="gender_id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="GoalID", new_column_name="goal_id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="Weight", new_column_name="weight",
        existing_type=mysql.DECIMAL(precision=7, scale=1),
        type_=mysql.DECIMAL(precision=7, scale=1),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="Height", new_column_name="height",
        existing_type=mysql.INTEGER(),
        type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="DateOfBirth", new_column_name="date_of_birth",
        existing_type=sa.Date(), type_=mysql.DATE(),
        existing_nullable=False
    )

    op.alter_column(
        "users_targets",
        column_name="ID", new_column_name="id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users_targets",
        column_name="UserID", new_column_name="user_id",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users_targets",
        column_name="Calories", new_column_name="calories",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users_targets",
        column_name="Protein", new_column_name="protein",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users_targets",
        column_name="Fat", new_column_name="fat",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users_targets",
        column_name="Carbs", new_column_name="carbs",
        existing_type=mysql.INTEGER(), type_=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.drop_column(
        "users_targets",
        column_name="MealUTCDateTime"
    )


def downgrade() -> None:
    print(f"running downgrade for revision {revision}")

    op.alter_column(
        "timezones",
        column_name="id", new_column_name="ID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "timezones",
        column_name="timezone", new_column_name="TimeZone",
        type_=sa.String(length=200), existing_type=mysql.VARCHAR(length=200),
        existing_nullable=False
    )

    op.alter_column(
        "genders",
        column_name="id", new_column_name="ID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "genders",
        column_name="gender", new_column_name="Gender",
        type_=sa.String(length=50), existing_type=mysql.VARCHAR(length=50),
        existing_nullable=False
    )

    op.alter_column(
        "goals",
        column_name="id", new_column_name="ID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "goals",
        column_name="goal", new_column_name="Goal",
        type_=sa.String(length=200), existing_type=mysql.VARCHAR(length=200),
        existing_nullable=False
    )

    op.alter_column(
        "meals_eaten",
        column_name="id", new_column_name="ID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )

    op.alter_column(
        "meals_eaten",
        column_name="user_id", new_column_name="UserID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="created_utc_datetime", new_column_name="CreatedUTCDateTime",
        type_=sa.DateTime(), existing_type=mysql.DATETIME(),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="created_local_datetime", new_column_name="CreatedLocalDateTime",
        type_=sa.DateTime(), existing_type=mysql.DATETIME(),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="name", new_column_name="Name",
        type_=sa.String(length=100), existing_type=mysql.VARCHAR(length=100),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="weight", new_column_name="Weight",
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="calories", new_column_name="Calories",
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="carbs", new_column_name="Carbs",
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="protein", new_column_name="Protein",
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="fat", new_column_name="Fat",
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_eaten",
        column_name="description", new_column_name="Description",
        type_=sa.String(length=5000), existing_type=mysql.VARCHAR(length=5000),
        existing_nullable=True
    )

    op.alter_column(
        "meals_for_future_use",
        column_name="id", new_column_name="ID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="user_id", new_column_name="UserID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="created_utc_datetime", new_column_name="CreatedUTCDateTime",
        type_=sa.DateTime(), existing_type=mysql.DATETIME(),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="name", new_column_name="Name",
        type_=sa.String(length=100), existing_type=mysql.VARCHAR(length=100),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="default_weight_grams", new_column_name="DefaultWeightGrams",
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="calories_per_100g", new_column_name="CaloriesPer100g",
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="protein_per_100g", new_column_name="ProteinPer100g",
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="fat_per_100g", new_column_name="FatPer100g",
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="carbs_per_100g", new_column_name="CarbsPer100g",
        type_=mysql.DECIMAL(precision=10, scale=4),
        existing_type=mysql.DECIMAL(precision=10, scale=4),
        existing_nullable=False
    )
    op.alter_column(
        "meals_for_future_use",
        column_name="description", new_column_name="Description",
        existing_type=mysql.VARCHAR(length=5000),
        type_=sa.String(length=5000),
        existing_nullable=True
    )

    op.alter_column(
        "users",
        column_name="id", new_column_name="ID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="created_utc_datetime", new_column_name="CreatedUTCDateTime",
        type_=sa.DateTime(), existing_type=mysql.DATETIME(),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="name", new_column_name="Name",
        type_=sa.String(length=100), existing_type=mysql.VARCHAR(length=100),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="telegram_id", new_column_name="TelegramID",
        type_=sa.String(length=100), existing_type=mysql.VARCHAR(length=100),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="is_activated", new_column_name="IsActive",
        type_=mysql.TINYINT(display_width=1), existing_type=mysql.BOOLEAN(),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="timezone_id", new_column_name="TimeZoneID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="gender_id", new_column_name="GenderID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="goal_id", new_column_name="GoalID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="weight", new_column_name="Weight",
        type_=mysql.DECIMAL(precision=7, scale=1),
        existing_type=mysql.DECIMAL(precision=7, scale=1),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="height", new_column_name="Height",
        type_=mysql.INTEGER(),
        existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users",
        column_name="date_of_birth", new_column_name="DateOfBirth",
        type_=sa.Date(), existing_type=mysql.DATE(),
        existing_nullable=False
    )

    op.alter_column(
        "users_targets",
        column_name="id", new_column_name="ID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users_targets",
        column_name="user_id", new_column_name="UserID",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users_targets",
        column_name="calories", new_column_name="Calories",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users_targets",
        column_name="protein", new_column_name="Protein",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users_targets",
        column_name="fat", new_column_name="Fat",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.alter_column(
        "users_targets",
        column_name="carbs", new_column_name="Carbs",
        type_=mysql.INTEGER(), existing_type=mysql.INTEGER(unsigned=True),
        existing_nullable=False
    )
    op.add_column(
        table_name="users_targets",
        column=sa.Column('MealUTCDateTime', sa.DateTime(), server_default=sa.text('(utc_timestamp())'), nullable=False)
    )

    op.create_foreign_key(
        referent_table="timezones", source_table="users",
        local_cols=["TimeZoneID"], remote_cols=["ID"], constraint_name='users_ibfk_1'
    )
    op.create_foreign_key(
        referent_table="genders", source_table="users",
        local_cols=["GenderID"], remote_cols=["ID"], constraint_name='users_ibfk_2'
    )
    op.create_foreign_key(
        referent_table="goals", source_table="users",
        local_cols=["GoalID"], remote_cols=["ID"], constraint_name='users_ibfk_3'
    )
    op.create_foreign_key(
        referent_table="users", source_table="meals_eaten",
        local_cols=['UserID'], remote_cols=['ID'],
        constraint_name="meals_eaten_ibfk_1"
    )
    op.create_foreign_key(
        referent_table="users", source_table="meals_for_future_use",
        local_cols=['UserID'], remote_cols=['ID'],
        constraint_name="meals_for_future_use_ibfk_1"
    )
    op.create_foreign_key(
        referent_table="users", source_table="users_targets",
        local_cols=['UserID'], remote_cols=['ID'],
        constraint_name="users_targets_ibfk_1"
    )
    op.create_check_constraint(
        constraint_name=op.f('ck_users_users_chk_1'),
        table_name="users",
        condition='(`Weight` >= 0)'
    )
    op.create_index('Gender', table_name='genders', columns=['Gender'], unique=True)
    op.create_index('Goal', table_name='goals', columns=['Goal'], unique=True)
    op.create_index('UserID', table_name='meals_eaten', columns=['UserID'], unique=True)
    op.create_index('UserID', table_name='meals_for_future_use', columns=['UserID'], unique=True)
    op.create_index('TimeZone', table_name='timezones', columns=['TimeZone'], unique=True)
    op.create_index('GenderID', table_name='users', columns=['GenderID'], unique=True)
    op.create_index('GoalID', table_name='users', columns=['GoalID'], unique=True)
    op.create_index('TelegramID', table_name='users', columns=['TelegramID'], unique=True)
    op.create_index('TimeZoneID', table_name='users', columns=['TimeZoneID'], unique=True)
    op.create_index('UserID', table_name='users_targets', columns=['UserID'], unique=True)