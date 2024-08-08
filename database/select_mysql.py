from database.init_mysql import execute_query


def select_users(connection):
    query = "SELECT * from users"
    return execute_query(connection, query)


def select_user_by_id(connection, id):
    query = f"SELECT * from users WHERE TelegramID='{id}'"
    users = execute_query(connection, query)
    if len(users) > 0:
        return users[0]
    else:
        return None

