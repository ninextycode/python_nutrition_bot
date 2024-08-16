from mysql.connector import connect
from database import config


def open_new_connection():
    connection = connect(
        host=config.host,
        user=config.username,
        password=config.password,
    )
    return connection


def execute_query(connection, query, params=None):
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def use_database(connection):
    query = f"USE {config.database};"
    return execute_query(connection, query)


def open_database_connection():
    connection = open_new_connection()
    use_database(connection)
    return connection


def get_connection():
    # TODO use pool
    return open_database_connection()
