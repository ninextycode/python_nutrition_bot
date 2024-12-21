from database.common_mysql import execute_query
from database.select.select_common import select_first_row_query
import pytz


def select_users(connection):
    query = "SELECT * from users"
    return execute_query(connection, query)


def select_user_by_user_id(connection, user_id):
    query = (
        f"SELECT u.*, t.TimeZone, ge.Gender, go.Goal FROM users u "
        "JOIN timezones t ON u.TimeZoneID = t.ID "
        "JOIN goals go ON u.GoalID = go.ID "
        "JOIN genders ge ON u.GenderID = ge.ID "
        "WHERE u.ID=%s;"
    )
    return select_first_row_query(connection, query, [user_id])


def select_user_by_telegram_id(connection, tg_id):
    query = (
        f"SELECT u.*, t.TimeZone, ge.Gender, go.Goal FROM users u "
        "JOIN timezones t ON u.TimeZoneID = t.ID "
        "JOIN goals go ON u.GoalID = go.ID "
        "JOIN genders ge ON u.GenderID = ge.ID "
        "WHERE u.TelegramID=%s;"
    )
    return select_first_row_query(connection, query, [tg_id])


def get_gender_id(connection, gender):
    get_gender_id_query = \
        f"SELECT ID FROM genders WHERE Gender = %s;"
    gender_id = select_first_row_query(
        connection, get_gender_id_query, [gender]
    )
    if gender_id is None:
        return None
    else:
        return gender_id["ID"]


def get_goal_id(connection, goal):
    get_goal_id_query = \
        f"SELECT ID FROM goals WHERE Goal = %s;"
    goal_id = select_first_row_query(
        connection, get_goal_id_query, [goal]
    )
    if goal_id is None:
        return None
    else:
        return goal_id["ID"]


def localize_naive_time_to_user_tz(connection, user_id, *times):
    if len(times) == 0:
        return

    tz = get_timezone_object_by_user_id(connection, user_id)

    out_list = []
    for t in times:
        if t.tzinfo is None:
            t = tz.localize(t)
        out_list.append(t)

    if len(out_list) == 1:
        return out_list[0]
    else:
        return tuple(out_list)


def get_timezone_object_by_user_id(connection, user_id):
    query = (
        "SELECT t.TimeZone FROM users u "
        "JOIN timezones t ON u.TimeZoneID = t.ID "
        "WHERE u.ID=%s;"
    )
    tz_dict = select_first_row_query(connection, query, [user_id])
    return pytz.timezone(tz_dict["TimeZone"])
