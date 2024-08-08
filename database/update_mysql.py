from database.init_mysql import execute_query


def create_new_user(connection, name, tg_id, time_zone=None):
    if time_zone is not None:
        query = (
            "INSERT INTO users (Name, TelegramID, TimeZone) VALUES "
            f"( \"{name}\", \"{tg_id}\", \"{time_zone}\" )"
        )
    else:
        query = (
            "INSERT INTO users (Name, TelegramID) VALUES "
            f"( \"{name}\", \"{tg_id}\" )"
        )
    execute_query(connection, query)
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
