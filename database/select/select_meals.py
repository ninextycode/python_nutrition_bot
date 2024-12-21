from database.common_mysql import execute_query
from database.select import select_users
import pytz


def select_meals_for_future_use(connection, user_id):
    query = (
        "SELECT * FROM meals_for_future_use "
        "WHERE UserID = %s "
        "ORDER BY Name ASC;"
    )
    return execute_query(connection, query, [user_id])


def select_meals_eaten_closed_interval(connection, user_id, datetime_from, datetime_to, localize=True):
    return select_meals_eaten(connection, user_id, datetime_from, datetime_to, True, True, localize)


def select_meals_eaten_right_open_interval(connection, user_id, datetime_from, datetime_to, localize=True):
    return select_meals_eaten(connection, user_id, datetime_from, datetime_to, True, False, localize)


def select_meals_eaten(connection, user_id, datetime_from, datetime_to, left_closed, right_closed, localize):
    if localize:
        datetime_from, datetime_to = select_users.localize_naive_time_to_user_tz(
            connection, user_id, datetime_from, datetime_to
        )
    time_from_utc_naive = datetime_from.astimezone(pytz.utc).replace(tzinfo=None)
    time_to_utc_naive = datetime_to.astimezone(pytz.utc).replace(tzinfo=None)

    time_from_s = time_from_utc_naive.isoformat(sep=' ', timespec='seconds')
    time_to_s = time_to_utc_naive.isoformat(sep=' ', timespec='seconds')
    print(f"selecting meals from {time_from_s} to {time_to_s}")

    s_left = ">=" if left_closed else ">"
    s_right = "<=" if right_closed else "<"
    query = (
        "SELECT * FROM meals_eaten "
        "WHERE "
        "(UserID = %s) AND "
        "("
        f"CreatedUTCDateTime {s_left} %s AND "
        f"CreatedUTCDateTime {s_right} %s"
        ")"
        "ORDER BY CreatedUTCDateTime ASC;"
    )
    return execute_query(connection, query, [user_id, time_from_utc_naive, time_to_utc_naive])
