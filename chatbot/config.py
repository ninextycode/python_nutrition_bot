import pint


secret = open("secrets/telegram_secret.txt").read()
registration_password = open("secrets/registration_password.txt").read()

class Commands:
    NEW_USER = "new_user"
    NEW_MEAL = "new_meal"
    UPDATE_USER = "update_user"
    GET_USER_DATA = "get_user_data"
    DELETE_USER = "delete_user"


u_reg = pint.UnitRegistry()
