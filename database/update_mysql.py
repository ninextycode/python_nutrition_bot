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
    goal = goal.lower()
    gender = gender.lower()

    get_timezone_id_query = \
        "SELECT ID FROM timezones WHERE TimeZone = %s"

    timezone_id = select_first_row_query(
        connection, get_timezone_id_query, [time_zone]
    )

    if timezone_id is None:
        add_query = (
            "INSERT INTO timezones (TimeZone)"
            "VALUES (%s);"
        )
        execute_query(connection, add_query, [time_zone])
        timezone_id = select_first_row_query(
            connection, "SELECT LAST_INSERT_ID() AS ID;"
        )

    timezone_id = timezone_id["ID"]

    get_gender_id_query = \
        f"SELECT ID FROM genders WHERE Gender = %s;"
    gender_id = select_first_row_query(
        connection, get_gender_id_query, [gender]
    )["ID"]

    get_goal_id_query = \
        f"SELECT ID FROM goals WHERE Goal = %s;"
    goal_id = select_first_row_query(
        connection, get_goal_id_query, [goal]
    )["ID"]

    new_user_query = (
        "INSERT INTO users "
        "(Name, TelegramID, TimezoneID, GenderID, GoalID, Weight, Height) "
        "VALUES ( "
        f"%(name)s,"
        f"%(tg_id)s,"
        f"%(timezone_id)s,"
        f"%(gender_id)s,"
        f"%(goal_id)s,"
        f"%(weight)s,"
        f"%(height)s"
        ");"
    )

    parameters = dict(
        name=name,
        tg_id=tg_id,
        timezone_id=timezone_id,
        gender_id=gender_id,
        goal_id=goal_id,
        weight=round(weight, 1),
        height=round(height)
    )

    execute_query(connection, new_user_query, parameters)
    connection.commit()


def activate_user(connection, user_id):
    query = (
        "UPDATE users "
        f"SET IsActive=TRUE "
        f"WHERE ID=%s"
    )
    execute_query(connection, query, [user_id])
    connection.commit()


def deactivate_user(connection, user_id):
    query = (
        "UPDATE users "
        f"SET IsActive=FALSE "
        f"WHERE ID=%s"
    )
    execute_query(connection, query, [user_id])
    connection.commit()
