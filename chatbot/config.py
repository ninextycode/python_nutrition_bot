import pint
import os
from enum import Enum, auto


is_production = bool(os.getenv("IS_PRODUCTION", False))

if is_production:
    secret = open("secrets/telegram_secret_production.txt").read()
else:
    secret = open("secrets/telegram_secret_dev.txt").read()


registration_password = open("secrets/registration_password.txt").read()
bot_username = "maxim_food_bot"


class Commands(Enum):
    START = "start"
    NEW_MEAL = "new_meal"
    VIEW_MEALS_EATEN = "view_meals"
    UPDATE_USER = "update_user"
    NEW_USER = "new_user"
    GET_USER_DATA = "get_user_data"
    VIEW_MEALS_SAVED_FOR_FUTURE_USE = "view_meals_saved"
    DELETE_USER = "delete_user"


class DataKeys(Enum):
    MEAL_DATA = auto()
    MEALS_EATEN_DATAVIEW = auto()
    USER_DATA = auto()

u_reg = pint.UnitRegistry()
