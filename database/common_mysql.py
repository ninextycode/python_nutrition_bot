from mysql.connector import connect
from database import config


def open_connection():
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
