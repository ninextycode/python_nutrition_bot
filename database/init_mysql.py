from database import config
from database.common_mysql import execute_query, use_database
from database.select.select_common import get_number_of_rows


def create_database(connection):
    query = f"CREATE DATABASE IF NOT EXISTS {config.database};"
    return execute_query(connection, query)


def create_user_table(connection):
    query = (
        "CREATE TABLE IF NOT EXISTS users( "
        "ID INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, "
        "CreatedUTCDateTime DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP), "
        "Name VARCHAR(100) NOT NULL, "
        "TelegramID VARCHAR(100) NOT NULL UNIQUE, "
        "IsActive BOOL NOT NULL DEFAULT FALSE, "
        "TimeZoneID INT UNSIGNED NOT NULL DEFAULT 0, "
        "GenderID INT UNSIGNED NOT NULL, "
        "GoalID INT UNSIGNED NOT NULL, "
        "Weight DECIMAL(7, 1) NOT NULL CHECK (Weight >= 0), "
        "Height INT UNSIGNED NOT NULL, "
        "DateOfBirth DATE NOT NULL,"
        "FOREIGN KEY (TimeZoneID) REFERENCES timezones(ID), "
        "FOREIGN KEY (GenderID) REFERENCES genders(ID), "
        "FOREIGN KEY (GoalID) REFERENCES goals(ID)"
        ")"
    )
    return execute_query(connection, query)


def create_meals_eaten_table(connection):
    query = (
        "CREATE TABLE IF NOT EXISTS meals_eaten( "
        "ID INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, "
        "UserID INT UNSIGNED NOT NULL, "
        
        "CreatedUTCDateTime DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP), "
        "CreatedLocalDateTime DATETIME NOT NULL, "
        
        "Name VARCHAR(100) NOT NULL, "
        "Description VARCHAR(5000), "
        
        "Weight DECIMAL(10, 4) UNSIGNED NOT NULL, "
        "Calories DECIMAL(10, 4) UNSIGNED NOT NULL, "
        "Carbs DECIMAL(10, 4) UNSIGNED NOT NULL, "
        "Protein DECIMAL(10, 4) UNSIGNED NOT NULL, "
        "Fat DECIMAL(10, 4) UNSIGNED NOT NULL, "
        
        "FOREIGN KEY (UserID) REFERENCES users(ID) "
        ")"
    )
    return execute_query(connection, query)


def create_users_targets_table(connection):
    query = (
        "CREATE TABLE IF NOT EXISTS users_targets( "
        "ID INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, "
        "UserID INT UNSIGNED UNIQUE NOT NULL, "
        "Calories INT UNSIGNED NOT NULL, "
        "Protein INT UNSIGNED NOT NULL, "
        "Fat INT UNSIGNED NOT NULL, "
        "Carbs INT UNSIGNED NOT NULL, "
        "MealUTCDateTime DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP), "

        "FOREIGN KEY (UserID) REFERENCES users(ID)"
        ")"
    )
    return execute_query(connection, query)


def create_genders_table(connection):
    query_init = (
        "CREATE TABLE IF NOT EXISTS genders( "
        "ID INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, "
        "Gender VARCHAR(50) UNIQUE NOT NULL "
        ")"
    )
    execute_query(connection, query_init)
    # add rows, but only to the newly created database
    if get_number_of_rows(connection, "genders") == 0:
        query_insert = (
            "INSERT INTO genders (Gender) VALUES "
            """( "male" ), ( "female" );"""
        )
        execute_query(connection, query_insert)


def create_timezones_table(connection):
    query_init = (
        "CREATE TABLE IF NOT EXISTS timezones( "
        "ID INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, "
        "TimeZone VARCHAR(200) UNIQUE NOT NULL "
        ")"
    )
    execute_query(connection, query_init)
    # add rows, but only to the newly created database
    if get_number_of_rows(connection, "timezones") == 0:
        query_insert = (
            "INSERT INTO timezones (ID, TimeZone) VALUES "
            """( 0, "utc" );"""
        )
        execute_query(connection, query_insert)


def create_goals_table(connection):
    query_init = (
        "CREATE TABLE IF NOT EXISTS goals( "
        "ID INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, "
        "Goal VARCHAR(200) UNIQUE NOT NULL "
        ")"
    )
    execute_query(connection, query_init)
    # add rows, but only to the newly created database
    if get_number_of_rows(connection, "goals") == 0:
        query_insert = (
            "INSERT INTO goals (Goal) VALUES "
            """( "lose weight" ), """
            """( "lose weight slowly" ), """
            """( "maintain weight" ), """
            """( "gain muscle slowly" ), """
            """( "gain muscle" );"""
        )
        execute_query(connection, query_insert)


def create_meals_for_future_use_table(connection):
    query = (
        "CREATE TABLE IF NOT EXISTS meals_for_future_use( "
        "ID INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, "
        "UserID INT UNSIGNED NOT NULL, "
        
        "CreatedUTCDateTime DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP), "
        
        "Name VARCHAR(100) NOT NULL, "
        "Description VARCHAR(5000), "
        
        "DefaultWeightGrams DECIMAL(10, 4) UNSIGNED NOT NULL, "
        "CaloriesPer100g DECIMAL(10, 4) UNSIGNED NOT NULL, "
        "ProteinPer100g DECIMAL(10, 4) UNSIGNED NOT NULL, "
        "FatPer100g DECIMAL(10, 4) UNSIGNED NOT NULL, "
        "CarbsPer100g DECIMAL(10, 4) UNSIGNED NOT NULL, "
        
        "FOREIGN KEY (UserID) REFERENCES users(ID), "
        "UNIQUE (UserID, Name) "
        ")"
    )
    return execute_query(connection, query)


def create_schema(connection):
    create_database(connection)
    use_database(connection)

    create_genders_table(connection)
    create_goals_table(connection)
    create_timezones_table(connection)

    create_user_table(connection)
    create_meals_eaten_table(connection)
    create_users_targets_table(connection)
    create_meals_for_future_use_table(connection)

    connection.commit()
