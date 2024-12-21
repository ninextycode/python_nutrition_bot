from database.common_mysql import execute_query, validate_table_name
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


def get_number_of_rows(connection, database_name):
    validate_table_name(database_name)
    data = select_first_row_query(
        connection, f"SELECT COUNT(*) AS size FROM {database_name};"
    )
    return data["size"]
