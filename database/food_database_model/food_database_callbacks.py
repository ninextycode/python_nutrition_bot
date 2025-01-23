from database.food_database_model.food_database_objects import *
from database.food_database_model.utils import *
from database import common_sql
import sqlalchemy as sa


@sa.event.listens_for(User, "before_insert")
def before_insert_user(mapper, connection, target: User):
    if target.created_utc_datetime is None:
        target.created_utc_datetime = datetime.datetime.now(datetime.UTC)


@sa.event.listens_for(MealEaten, "before_insert")
def before_insert_meal_eaten(mapper, connection, target: MealEaten):
    if target.created_utc_datetime is None:
        if target.created_local_datetime is None:
            target.created_utc_datetime = datetime.datetime.now(datetime.UTC)
        else:
            with sa.orm.Session(bind=connection) as session:
                local_datetime = localize_to_user_tz(
                    session, target.user_id, target.created_local_datetime
                )
                target.created_utc_datetime = local_datetime.astimezone(pytz.utc)

    if target.created_local_datetime is None:
        with sa.orm.Session(bind=connection) as session:
            target.created_local_datetime = convert_to_user_tz(
                session, target.user_id,
                target.created_utc_datetime
            )


@sa.event.listens_for(MealForFutureUse, "before_insert")
def before_insert_meal_for_future_use(mapper, connection, target: MealForFutureUse):
    if target.created_utc_datetime is None:
        target.created_utc_datetime = datetime.datetime.now(datetime.UTC)
