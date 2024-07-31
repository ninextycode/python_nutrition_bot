from database.init_mysql import execute_query


def get_users(connection):
    query = "SELECT * from users"
    return execute_query(connection, query)
