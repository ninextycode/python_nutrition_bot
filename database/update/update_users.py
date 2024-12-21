from database.init_mysql import execute_query
from database.select.select_common import select_first_row_query
from database.select.select_users import get_gender_id, get_goal_id


def create_new_user(
    connection,
    name,
    gender,
    goal,
    weight,
    height,
    date_of_birth,
    tg_id,
    time_zone=None
):
    goal = goal.lower()
    gender = gender.lower()

    timezone_id = get_timezone_id_insert_if_missing(connection, time_zone)

    gender_id = get_gender_id(connection, gender)
    goal_id = get_goal_id(connection, goal)
    if goal_id is None:
        raise KeyError(f"Goal \"{goal}\" was not found in goals database.")

    # set IsActive to True, no not implement any registration/activation functionality for now
    new_user_query = (
        "INSERT INTO users "
        "(Name, TelegramID, TimezoneID, GenderID, GoalID, Weight, Height, DateOfBirth, IsActive) "
        "VALUES ( "
        "%(name)s, "
        "%(tg_id)s, "
        "%(timezone_id)s, "
        "%(gender_id)s, "
        "%(goal_id)s, "
        "%(weight)s, "
        "%(height)s, "
        "%(date_of_birth)s, "
        "TRUE"
        ");"
    )

    parameters = dict(
        name=name,
        tg_id=tg_id,
        timezone_id=timezone_id,
        gender_id=gender_id,
        goal_id=goal_id,
        weight=round(weight, 1),
        height=round(height),
        date_of_birth=date_of_birth
    )
    result = execute_query(connection, new_user_query, parameters)
    connection.commit()
    return result


def update_user(
        connection,
        tg_id,
        name=None,
        gender=None,
        goal=None,
        weight=None,
        height=None,
        date_of_birth=None,
        time_zone=None
):
    if goal is not None:
        goal = goal.lower()
    if gender is not None:
        gender = gender.lower()

    parameters = dict(
        tg_id=str(tg_id),
    )

    values_strs = []

    if name is not None:
        s = "Name = %(name)s"
        values_strs.append(s)
        parameters["name"] = name

    if gender is not None:
        s = "GenderID = %(gender_id)s"
        values_strs.append(s)
        parameters["gender_id"] = get_gender_id(connection, gender)

    if goal is not None:
        s = "GoalID = %(goal_id)s"
        values_strs.append(s)
        parameters["goal_id"] = get_goal_id(connection, goal)

    if weight is not None:
        s = "Weight = %(weight)s"
        values_strs.append(s)
        parameters["weight"] = round(weight, 1)

    if height is not None:
        s = "Height = %(height)s"
        values_strs.append(s)
        parameters["height"] = round(height)

    if date_of_birth is not None:
        s = "DateOfBirth = %(date_of_birth)s"
        values_strs.append(s)
        parameters["date_of_birth"] = date_of_birth

    if time_zone is not None:
        s = "TimezoneID = %(timezone_id)s"
        values_strs.append(s)
        parameters["timezone_id"] = get_timezone_id_insert_if_missing(
            connection, time_zone
        )

    values = ", ".join(values_strs)

    update_user_query = (
        "UPDATE users "
        f"SET {values} "
        "WHERE TelegramID = %(tg_id)s ;"
    )
    result = execute_query(connection, update_user_query, parameters)
    connection.commit()
    return result


def get_timezone_id_insert_if_missing(connection, time_zone):
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
        add_query_result = execute_query(connection, add_query, [time_zone])
        timezone_id = select_first_row_query(
            connection, "SELECT LAST_INSERT_ID() AS ID;"
        )
    timezone_id = timezone_id["ID"]
    return timezone_id


def activate_user(connection, user_id):
    query = (
        "UPDATE users "
        "SET IsActive=TRUE "
        "WHERE ID=%s"
    )
    result = execute_query(connection, query, [user_id])
    connection.commit()
    return result


def deactivate_user(connection, user_id):
    query = (
        "UPDATE users "
        "SET IsActive=FALSE "
        "WHERE ID=%s"
    )
    result = execute_query(connection, query, [user_id])
    connection.commit()
    return result
