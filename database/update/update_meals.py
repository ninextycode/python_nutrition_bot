import sqlalchemy as sa
from database.food_database_model import *
import numpy as np


def add_new_eaten_meal(
    session, meal_eaten
):
    session.add(meal_eaten)
    session.commit()


def add_new_meal_for_future_use(
    session, meal_for_future_use
):
    session.add(meal_for_future_use)
    session.commit()


def add_new_meal_for_future_use_from_meal_eaten(
    session, meal_eaten, default_weight=None
):
    if default_weight is None:
        default_weight = meal_eaten.weight

    if default_weight is None or default_weight <= 0:
        raise ValueError("weight must be positive")

    values = np.array([
        (v if v is not None else 0) for v in
        [meal_eaten.calories, meal_eaten.protein, meal_eaten.fat, meal_eaten.carbs]
    ])
    values_per_100 = values / meal_eaten.weight * 100

    calories_per_100, protein_per_100, fat_per_100, carbs_per_100 = values_per_100

    meal_for_future_use = MealForFutureUse(
        user_id=meal_eaten.user_id,
        name=meal_eaten.name,
        description=meal_eaten.description,
        default_weight_grams=default_weight,
        calories_per_100g=calories_per_100,
        protein_per_100g=protein_per_100,
        fat_per_100g=fat_per_100,
        carbs_per_100g=carbs_per_100
    )
    session.add(meal_for_future_use)
    session.commit()


def delete_meal_eaten(
    session, meal_value
):
    if isinstance(meal_value, MealEaten):
        session.delete(meal_value)
    else:
        sql = sa.delete(MealEaten).where(MealEaten.id == meal_value)
        session.execute(sql)
    session.commit()


def delete_meal_for_future_use(
    session, meal_value
):
    if isinstance(meal_value, MealForFutureUse):
        session.delete(meal_value)
    else:
        sql = sa.delete(MealForFutureUse).where(MealEaten.id == meal_value)
        session.execute(sql)
    session.commit()

