from database.food_database_model.food_database_objects import *
from database import common_sql
from enum import Enum


class MaleFemaleSqlValue(Enum):
    MALE = "male"
    FEMALE = "female"


class GoalSqlValue(Enum):
    LOSE_WEIGHT = "lose weight"
    LOSE_WEIGHT_SLOWLY = "lose weight slowly"
    MAINTAIN_WEIGHT = "maintain weight"
    GAIN_MUSCLE_SLOWLY = "gain muscle slowly"
    GAIN_MUSCLE = "gain muscle"


def get_male(session):
    return session.scalar(
        sa.select(Gender).where(Gender.gender == MaleFemaleSqlValue.MALE.value)
    )


def get_female(session):
    return session.scalar(
        sa.select(Gender).where(Gender.gender == MaleFemaleSqlValue.FEMALE.value)
    )


def get_goal(session, goal):
    if isinstance(goal, Enum):
        goal = str(goal.value)
    goal = goal.lower()
    return session.scalar(
        sa.select(Goal).where(Goal.goal == goal)
    )


with common_sql.get_session() as _session:
    class MaleFemaleEntry(Enum):
        MALE = get_male(_session)
        FEMALE = get_female(_session)


    class GoalEntry(Enum):
        LOSE_WEIGHT = get_goal(_session, GoalSqlValue.LOSE_WEIGHT)
        LOSE_WEIGHT_SLOWLY = get_goal(_session, GoalSqlValue.LOSE_WEIGHT_SLOWLY)
        MAINTAIN_WEIGHT = get_goal(_session, GoalSqlValue.MAINTAIN_WEIGHT)
        GAIN_MUSCLE_SLOWLY = get_goal(_session, GoalSqlValue.GAIN_MUSCLE_SLOWLY)
        GAIN_MUSCLE = get_goal(_session, GoalSqlValue.GAIN_MUSCLE)
