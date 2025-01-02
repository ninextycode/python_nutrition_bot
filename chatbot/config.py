import pint


secret = open("secrets/telegram_secret.txt").read()
registration_password = open("secrets/registration_password.txt").read()
bot_username = "maxim_food_bot"


class Commands:
    NEW_USER = "new_user"
    NEW_MEAL = "new_meal"
    UPDATE_USER = "update_user"
    GET_USER_DATA = "get_user_data"
    DELETE_USER = "delete_user"
    VIEW_MEALS_EATEN = "view_meals"
    VIEW_MEALS_SAVED_FOR_FUTURE_USE = "view_meals_saved"


bot_info = None

u_reg = pint.UnitRegistry()
