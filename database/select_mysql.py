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
    query = f"SELECT * from users WHERE TelegramID=%s"
    users = execute_query(connection, query, [tg_id])
    if len(users) > 0:
        return users[0]
    else:
        return None
