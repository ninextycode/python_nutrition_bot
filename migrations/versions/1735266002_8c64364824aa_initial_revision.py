"""initial revision

Revision ID: 8c64364824aa
Revises: 
Create Date: 2024-12-21 23:33:05.292998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '8c64364824aa'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print(f"running upgrade for revision {revision}")
    # ### commands auto generated by Alembic - please adjust! ###
    genders_table = op.create_table('genders',
    sa.Column('ID', mysql.INTEGER(), nullable=False),
    sa.Column('Gender', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('ID', name=op.f('pk_genders'))
    )
    op.create_index('Gender', 'genders', ['Gender'], unique=True)
    goals_table = op.create_table('goals',
    sa.Column('ID', mysql.INTEGER(), nullable=False),
    sa.Column('Goal', sa.String(length=200), nullable=False),
    sa.PrimaryKeyConstraint('ID', name=op.f('pk_goals'))
    )
    op.create_index('Goal', 'goals', ['Goal'], unique=True)
    timezones_table = op.create_table('timezones',
    sa.Column('ID', mysql.INTEGER(), nullable=False),
    sa.Column('TimeZone', sa.String(length=200), nullable=False),
    sa.PrimaryKeyConstraint('ID', name=op.f('pk_timezones'))
    )
    op.create_index('TimeZone', 'timezones', ['TimeZone'], unique=True)
    op.create_table('users',
    sa.Column('ID', mysql.INTEGER(), nullable=False),
    sa.Column('CreatedUTCDateTime', sa.DateTime(), server_default=sa.text('(utc_timestamp())'), nullable=False),
    sa.Column('Name', sa.String(length=100), nullable=False),
    sa.Column('TelegramID', sa.String(length=100), nullable=False),
    sa.Column('IsActive', mysql.TINYINT(display_width=1), server_default=sa.text("'0'"), nullable=False),
    sa.Column('TimeZoneID', mysql.INTEGER(), server_default=sa.text("'0'"), nullable=False),
    sa.Column('GenderID', mysql.INTEGER(), nullable=False),
    sa.Column('GoalID', mysql.INTEGER(), nullable=False),
    sa.Column('Weight', mysql.DECIMAL(precision=5, scale=1), nullable=False),
    sa.Column('Height', mysql.INTEGER(), nullable=False),
    sa.Column('DateOfBirth', sa.Date(), nullable=False),
    sa.CheckConstraint('(`Weight` >= 0)', name=op.f('ck_users_users_chk_1')),
    sa.ForeignKeyConstraint(['TimeZoneID'], ['timezones.ID'], name='users_ibfk_1'),
    sa.ForeignKeyConstraint(['GenderID'], ['genders.ID'], name='users_ibfk_2'),
    sa.ForeignKeyConstraint(['GoalID'], ['goals.ID'], name='users_ibfk_3'),
    sa.PrimaryKeyConstraint('ID', name=op.f('pk_users'))
    )
    op.create_index('GenderID', 'users', ['GenderID'], unique=False)
    op.create_index('GoalID', 'users', ['GoalID'], unique=False)
    op.create_index('TelegramID', 'users', ['TelegramID'], unique=True)
    op.create_index('TimeZoneID', 'users', ['TimeZoneID'], unique=False)
    op.create_table('meals_eaten',
    sa.Column('ID', mysql.INTEGER(), nullable=False),
    sa.Column('UserID', mysql.INTEGER(), nullable=False),
    sa.Column('CreatedUTCDateTime', sa.DateTime(), server_default=sa.text('(utc_timestamp())'), nullable=False),
    sa.Column('CreatedLocalDateTime', sa.DateTime(), nullable=False),
    sa.Column('Name', sa.String(length=100), nullable=False),
    sa.Column('Weight', mysql.DECIMAL(precision=10, scale=4), nullable=False),
    sa.Column('Calories', mysql.DECIMAL(precision=10, scale=4), nullable=False),
    sa.Column('Carbs', mysql.DECIMAL(precision=10, scale=4), nullable=False),
    sa.Column('Protein', mysql.DECIMAL(precision=10, scale=4), nullable=False),
    sa.Column('Fat', mysql.DECIMAL(precision=10, scale=4), nullable=False),
    sa.Column('Description', sa.String(length=5000), nullable=True),
    sa.ForeignKeyConstraint(['UserID'], ['users.ID'], name='meals_eaten_ibfk_1'),
    sa.PrimaryKeyConstraint('ID', name=op.f('pk_meals_eaten'))
    )
    op.create_index('UserID', 'meals_eaten', ['UserID'], unique=False)
    op.create_table('meals_for_future_use',
    sa.Column('ID', mysql.INTEGER(), nullable=False),
    sa.Column('UserID', mysql.INTEGER(), nullable=False),
    sa.Column('CreatedUTCDateTime', sa.DateTime(), server_default=sa.text('(utc_timestamp())'), nullable=False),
    sa.Column('Name', sa.String(length=100), nullable=False),
    sa.Column('DefaultWeightGrams', mysql.DECIMAL(precision=10, scale=4), nullable=False),
    sa.Column('CaloriesPer100g', mysql.DECIMAL(precision=10, scale=4), nullable=False),
    sa.Column('ProteinPer100g', mysql.DECIMAL(precision=10, scale=4), nullable=False),
    sa.Column('FatPer100g', mysql.DECIMAL(precision=10, scale=4), nullable=False),
    sa.Column('CarbsPer100g', mysql.DECIMAL(precision=10, scale=4), nullable=False),
    sa.Column('Description', sa.String(length=5000), nullable=True),
    sa.ForeignKeyConstraint(['UserID'], ['users.ID'], name='meals_for_future_use_ibfk_1'),
    sa.PrimaryKeyConstraint('ID', name=op.f('pk_meals_for_future_use'))
    )
    op.create_index('UserID', 'meals_for_future_use', ['UserID', 'Name'], unique=True)
    op.create_table('users_targets',
    sa.Column('ID', mysql.INTEGER(), nullable=False),
    sa.Column('UserID', mysql.INTEGER(), nullable=False),
    sa.Column('Calories', mysql.INTEGER(), nullable=False),
    sa.Column('Protein', mysql.INTEGER(), nullable=False),
    sa.Column('Fat', mysql.INTEGER(), nullable=False),
    sa.Column('Carbs', mysql.INTEGER(), nullable=False),
    sa.Column('MealUTCDateTime', sa.DateTime(), server_default=sa.text('(utc_timestamp())'), nullable=False),
    sa.ForeignKeyConstraint(['UserID'], ['users.ID'], name='users_targets_ibfk_1'),
    sa.PrimaryKeyConstraint('ID', name=op.f('pk_users_targets'))
    )
    op.create_index('UserID', 'users_targets', ['UserID'], unique=True)
    # ### end Alembic commands ###

    # Data insertion
    insert_1 = mysql.insert(goals_table).values(
        [
            {"ID": 1, "Goal": "lose weight"},
            {"ID": 2, "Goal": "lose weight slowly"},
            {"ID": 3, "Goal": "maintain weight"},
            {"ID": 4, "Goal": "gain muscle slowly"},
            {"ID": 5, "Goal": "gain muscle"}
        ]
    )
    insert_2 = mysql.insert(genders_table).values(
        [
            {"ID": 1, "Gender": "Male"},
            {"ID": 2, "Gender": "Female"}
        ]
    )
    insert_3 = mysql.insert(timezones_table).values(
        [{"ID": 1, "TimeZone": "UTC"}]
    )
    insert_1 = insert_1.on_duplicate_key_update(Goal=insert_1.inserted.Goal)
    insert_2 = insert_2.on_duplicate_key_update(Gender=insert_2.inserted.Gender)
    insert_3 = insert_3.on_duplicate_key_update(TimeZone=insert_3.inserted.TimeZone)

    op.execute(insert_1)
    op.execute(insert_2)
    op.execute(insert_3)


def downgrade() -> None:
    print(f"running downgrade for revision {revision}")
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("users_ibfk_2", type_="foreignkey")
        batch_op.drop_constraint("users_ibfk_3", type_="foreignkey")
        batch_op.drop_constraint("users_ibfk_1", type_="foreignkey")

    op.drop_constraint(
        table_name="users", type_="check",
        constraint_name=op.f("ck_users_users_chk_1")
    )
    op.drop_constraint("meals_eaten_ibfk_1", "meals_eaten", type_="foreignkey")
    op.drop_constraint("meals_for_future_use_ibfk_1", "meals_for_future_use", type_="foreignkey")
    op.drop_constraint("users_targets_ibfk_1", "users_targets", type_="foreignkey")

    op.drop_index('UserID', table_name='users_targets')
    op.drop_table('users_targets')
    op.drop_index('UserID', table_name='meals_for_future_use')
    op.drop_table('meals_for_future_use')
    op.drop_index('UserID', table_name='meals_eaten')
    op.drop_table('meals_eaten')
    op.drop_index('TimeZoneID', table_name='users')
    op.drop_index('TelegramID', table_name='users')
    op.drop_index('GoalID', table_name='users')
    op.drop_index('GenderID', table_name='users')
    op.drop_table('users')
    op.drop_index('TimeZone', table_name='timezones')
    op.drop_table('timezones')
    op.drop_index('Goal', table_name='goals')
    op.drop_table('goals')
    op.drop_index('Gender', table_name='genders')
    op.drop_table('genders')
    # ### end Alembic commands ###