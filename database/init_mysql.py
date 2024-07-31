from mysql.connector import connect
from database import config
from database.common_mysql import execute_query, use_database


def create_database(connection):
    query = f"CREATE DATABASE IF NOT EXISTS {config.database};"
    return execute_query(connection, query)


def create_user_table(connection):
    query = (
        "CREATE TABLE IF NOT EXISTS users("
        "ID INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,"
        "CreatedUTCDateTime DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP),"
        "Name VARCHAR(100) NOT NULL,"
        "TelegramID VARCHAR(100) NOT NULL UNIQUE,"
        "IsActive BOOL NOT NULL DEFAULT FALSE,"
        "TimeZone VARCHAR(50) NOT NULL DEFAULT \"UTC\""
        ")"
    )
    return execute_query(connection, query)


def create_meals_table(connection):
    query = (
        "CREATE TABLE IF NOT EXISTS meals("
        "ID INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,"
        "UserID INT UNSIGNED NOT NULL,"
        "Calories INT UNSIGNED NOT NULL,"
        "Carbohydrate INT UNSIGNED NOT NULL,"
        "Protein INT UNSIGNED NOT NULL,"
        "Fat INT UNSIGNED NOT NULL,"
        "MealUTCDateTime DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP),"
        "Name VARCHAR(100),"
        "Description VARCHAR(1000),"
        
        "FOREIGN KEY (UserID) REFERENCES users(ID)"
        ")"
    )
    return execute_query(connection, query)


def create_schema(connection):
    create_database(connection)
    use_database(connection)
    create_user_table(connection)
    create_meals_table(connection)
