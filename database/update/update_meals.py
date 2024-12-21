from database.common_mysql import execute_query
import numpy as np


def create_new_eaten_meal(
    connection,
    user_id,
    meal_name,
    description=None,
    weight=0,
    calories=0,
    protein=0,
    fat=0,
    carbs=0,
    overwrite_create_time=None
):

    new_user_query = (
        "INSERT INTO meals_eaten "
        f"("
        "UserID, Name, Description, Weight, Calories, Protein, Fat, Carbs"
        f"{", CreatedUTCDateTime" if overwrite_create_time is not None else ""}"
        ") "
        "VALUES ( "
        "%(user_id)s, "
        "%(name)s, "
        "%(description)s, "
        "%(weight)s, "
        "%(calories)s, "
        "%(protein)s, "
        "%(fat)s, "
        "%(carbs)s"
        f"{", %(create_time)s" if overwrite_create_time is not None else ""}"
        ");"
    )
    parameters = dict(
        user_id=user_id,
        name=meal_name,
        description=description,
        weight=weight,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs
    )
    if overwrite_create_time is not None:
        parameters["create_time"] = overwrite_create_time
    result = execute_query(connection, new_user_query, parameters)
    connection.commit()
    return result


def create_new_meal_for_future_use(
    connection,
    user_id,
    meal_name,
    description=None,
    weight=0,
    calories=0,
    protein=0,
    fat=0,
    carbs=0
):
    if weight <= 0:
        raise ValueError("weight myst be positive")
    values = np.array([
        calories, protein, fat, carbs
    ])
    values_per_100 = values / weight
    calories_per_100, protein_per_100, fat_per_100, carbs_per_100 = values_per_100
    return create_new_meal_for_future_use_per_100(
        connection,
        user_id,
        meal_name,
        description,
        weight,
        calories_per_100,
        protein_per_100,
        fat_per_100,
        carbs_per_100
    )


def create_new_meal_for_future_use_per_100(
    connection,
    user_id,
    meal_name,
    description=None,
    default_weight=0,
    calories_per_100=0,
    protein_per_100=0,
    fat_per_100=0,
    carbs_per_100=0
):
    # need to add (2) / (3) .. etc to names that already exist
    new_user_query = (
        "INSERT INTO meals_for_future_use "
        "(UserID, Name, Description, DefaultWeightGrams, CaloriesPer100g, ProteinPer100g, FatPer100g, CarbsPer100g) "
        "VALUES ( "
        f"%(user_id)s, "
        f"%(name)s, "
        f"%(description)s, "
        f"%(default_weight)s, "
        f"%(calories_per_100)s, "
        f"%(protein_per_100)s, "
        f"%(fat_per_100)s, "
        f"%(carbs_per_100)s"
        ");"
    )

    parameters = dict(
        user_id=user_id,
        name=meal_name,
        description=description,
        default_weight=default_weight,
        calories_per_100=calories_per_100,
        fat_per_100=fat_per_100,
        carbs_per_100=carbs_per_100,
        protein_per_100=protein_per_100
    )
    result = execute_query(connection, new_user_query, parameters)
    connection.commit()
    return result


def delete_eaten_meal(
    connection,
    meal_id
):
    delete_query = (
        "DELETE FROM meals_eaten "
        "WHERE ID=%s;"
    )
    result = execute_query(connection, delete_query, [meal_id])
    connection.commit()
    return result


def delete_meal_for_future_use(
    connection,
    meal_id
):
    delete_query = (
        "DELETE FROM meals_for_future_use "
        "WHERE ID=%s;"
    )
    result = execute_query(connection, delete_query, [meal_id])
    connection.commit()
    return result
