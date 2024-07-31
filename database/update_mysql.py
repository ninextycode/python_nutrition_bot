from database.init_mysql import execute_query


def create_new_user(connection, name, tg_id):
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
