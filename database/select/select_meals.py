import datetime

from database.food_database_model import *
import sqlalchemy as sa


def select_meals_for_future_use(session, user_id):
    meals = session.scalars(
        sa.select(MealForFutureUse).where(
            MealForFutureUse.user_id == user_id
        ).order_by(
            MealForFutureUse.name.asc()
        )
    )
    return meals


def select_meals_eaten_include_to(
        session: sa.orm.Session, user_id,
        datetime_from: datetime.datetime,
        datetime_to: datetime.datetime, as_utc=False
) -> list[MealEaten]:
    return select_meals_eaten_by_datetime(session, user_id, datetime_from, datetime_to, True, True, as_utc)


def select_meals_eaten_right_exclude_to(
        session: sa.orm.Session, user_id,
        datetime_from: datetime.datetime,
        datetime_to: datetime.datetime, as_utc=False
) -> list[MealEaten]:
    return select_meals_eaten_by_datetime(session, user_id, datetime_from, datetime_to, True, False, as_utc)


def select_meals_eaten_by_datetime(
        session: sa.orm.Session, user_id,
        datetime_from: datetime.datetime,
        datetime_to: datetime.datetime,
        left_closed, right_closed, as_utc
) -> list[MealEaten]:
    # make sure existing tzinfo is ignored
    datetime_from_naive = datetime_from.replace(tzinfo=None)
    datetime_to_naive = datetime_to.replace(tzinfo=None)

    if as_utc:
        datetime_column = MealEaten.created_utc_datetime
    else:
        datetime_column = MealEaten.created_local_datetime

    if left_closed:
        from_clause = (datetime_from_naive <= datetime_column)
    else:
        from_clause = (datetime_from_naive < datetime_column)

    if right_closed:
        to_clause = (datetime_column <= datetime_to_naive)
    else:
        to_clause = (datetime_column < datetime_to_naive)

    condition = sa.and_(
        (MealEaten.user_id == user_id),
        from_clause, to_clause
    )

    meals = session.scalars(
        sa.select(MealEaten).where(condition)
        .order_by(datetime_column.asc())
    ).fetchall()

    return meals


def select_meal_eaten_by_meal_id(
    session, meal_id
) -> MealEaten:
    return session.scalar(sa.select(MealEaten).where(MealEaten.id == meal_id))
