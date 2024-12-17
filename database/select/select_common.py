from database.common_mysql import execute_query
from database import config


def does_table_exist(connection, table_name, database_name=None):
    if database_name is None:
        database_name = config.database
    query = (
       "SELECT table_name FROM information_schema.tables " 
       f"WHERE table_schema = %(database_name)s" 
       f"AND table_name = %(table_name)s"
    )
    output = select_first_row_query(
        connection, query,
        dict(database_name=database_name, table_name=table_name)
    )
    return output is not None


def select_first_row_query(connection, query, params=None):
    data = execute_query(connection, query, params)
    if data is not None and len(data) > 0:
        return data[0]
    else:
        return None


def select_users(connection):
    query = "SELECT * from users"
    return execute_query(connection, query)


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
