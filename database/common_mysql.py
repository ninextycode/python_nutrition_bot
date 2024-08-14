from mysql.connector import connect
from database import config


def open_new_connection():
    connection = connect(
        host=config.host,
        user=config.username,
        password=config.password,
    )
    return connection


def execute_query(connection, query):
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def use_database(connection):
    query = f"USE {config.database};"
    return execute_query(connection, query)


def open_database_connection():
    connection = open_new_connection()
    use_database(connection)
    return connection


def does_table_exist(connection, table_name, database_name=None):
    if database_name is None:
        database_name = config.database
    query = (
       "SELECT table_name FROM information_schema.tables " 
       f"WHERE table_schema = \"{database_name}\" " 
       f"AND table_name = \"{table_name}\" "
    )
    return select_first_row_query(connection, query) is not None


def select_first_row_query(connection, query):
    data = execute_query(connection, query)
    if data is not None and len(data) > 0:
        return data[0]
    else:
        return None
