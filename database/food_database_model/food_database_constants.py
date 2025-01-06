from database.food_database_model.food_database_objects import *
from database import common_sql
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class ActivityLevelValue(Enum):
    LITTLE_TO_NO = "Little to no exercise"
    MODERATE_1_3_PER_WEEK = "Light exercise, 1-3 times per week"
    HIGH_3_5_PER_WEEK = "Moderate exercise, 3-5 times per week"
    VERY_HIGH_6_7_PER_WEEK = "Intense exercise, 6-7 times per week"
    HYPERACTIVE_2_HOURS_PER_DAY = "Very intense, 2 hours per day or more"


class MaleFemaleValue(Enum):
    MALE = "male"
    FEMALE = "female"


class GoalValue(Enum):
    LOSE_WEIGHT = "lose weight"
    LOSE_WEIGHT_SLOWLY = "lose weight slowly"
    MAINTAIN_WEIGHT = "maintain weight"
    GAIN_MUSCLE_SLOWLY = "gain muscle slowly"
    GAIN_MUSCLE = "gain muscle"


def get_male(session):
    return session.scalar(
        sa.select(Gender).where(Gender.gender == MaleFemaleValue.MALE.value)
    )


def get_female(session):
    return session.scalar(
        sa.select(Gender).where(Gender.gender == MaleFemaleValue.FEMALE.value)
    )


def get_goal(session, goal):
    if isinstance(goal, Enum):
        goal = str(goal.value)
    goal = goal.lower()
    return session.scalar(
        sa.select(Goal).where(Goal.goal == goal)
    )


def get_activity_level(session, activity_level):
    if isinstance(activity_level, Enum):
        activity_level = str(activity_level.name)
    return session.scalar(
        sa.select(ActivityLevel).where(
            ActivityLevel.name == activity_level
        )
    )


with common_sql.get_session() as _session:
    class MaleFemaleSqlEntry(Enum):
        MALE = get_male(_session)
        FEMALE = get_female(_session)


    class GoalSqlEntry(Enum):
        LOSE_WEIGHT = get_goal(_session, GoalValue.LOSE_WEIGHT)
        LOSE_WEIGHT_SLOWLY = get_goal(_session, GoalValue.LOSE_WEIGHT_SLOWLY)
        MAINTAIN_WEIGHT = get_goal(_session, GoalValue.MAINTAIN_WEIGHT)
        GAIN_MUSCLE_SLOWLY = get_goal(_session, GoalValue.GAIN_MUSCLE_SLOWLY)
        GAIN_MUSCLE = get_goal(_session, GoalValue.GAIN_MUSCLE)


    class ActivityLevelSqlEntry(Enum):
        LITTLE_TO_NO = get_activity_level(
            _session, ActivityLevelValue.LITTLE_TO_NO
        )
        MODERATE_1_3_PER_WEEK = get_activity_level(
            _session, ActivityLevelValue.MODERATE_1_3_PER_WEEK
        )
        HIGH_3_5_PER_WEEK = get_activity_level(
            _session, ActivityLevelValue.HIGH_3_5_PER_WEEK
        )
        VERY_HIGH_6_7_PER_WEEK = get_activity_level(
            _session, ActivityLevelValue.VERY_HIGH_6_7_PER_WEEK
        )
        HYPERACTIVE_2_HOURS_PER_DAY = get_activity_level(
            _session, ActivityLevelValue.HYPERACTIVE_2_HOURS_PER_DAY
        )
