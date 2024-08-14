from database.init_mysql import execute_query
from database.select_mysql import select_first_row_query


def create_new_user(
        connection,
        name,
        gender,
        goal,
        weight,
        height,
        tg_id,
        time_zone=None
):
    time_zone = time_zone.lower()
    goal = goal.lower()
    gender = gender.lower()

    get_timezone_id_query = \
        f"SELECT ID FROM timezones WHERE TimeZone = \"{time_zone}\""

    timezone_id = select_first_row_query(
        connection, get_timezone_id_query
    )["ID"]

    if timezone_id is None:
        add_query = (
            "INSERT INTO timezones (TimeZone)"
            f"VALUES (\"{time_zone}\");"
        )
        execute_query(connection, add_query)
        timezone_id = select_first_row_query(
            connection, "SELECT LAST_INSERT_ID() AS ID;"
        )
        timezone_id = timezone_id["ID"]

    get_gender_id_query = \
        f"SELECT ID FROM genders WHERE Gender = \"{gender}\""
    gender_id = select_first_row_query(
        connection, get_gender_id_query
    )["ID"]

    get_goal_id_query = \
        f"SELECT ID FROM goals WHERE Goal = \"{goal}\""
    goal_id = select_first_row_query(
        connection, get_goal_id_query
    )["ID"]

    new_user_query = (
        "INSERT INTO users "
        "(Name, TelegramID, TimezoneID, GenderID, GoalID, Weight, Height) "
        "VALUES ( "
        f"\"{name}\", "
        f"\"{tg_id}\", "
        f"{timezone_id}, "
        f"{gender_id}, "
        f"{goal_id}, "
        f"{weight:.1f}, "
        f"{height:.0f}"
        ");"
    )

    execute_query(connection, new_user_query)
    connection.commit()


def activate_user(connection, user_id):
    query = (
        "UPDATE users "
        f"SET IsActive=TRUE "
        f"WHERE ID={user_id}"
    )
    execute_query(connection, query)
    connection.commit()


def deactivate_user(connection, user_id):
    query = (
        "UPDATE users "
        f"SET IsActive=FALSE "
        f"WHERE ID={user_id} "
    )
    execute_query(connection, query)
    connection.commit()
