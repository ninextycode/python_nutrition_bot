import pint


secret = open("secrets/telegram_secret.txt").read()


class Commands:
    NEW_USER = "new_user"
    UPDATE_USER = "update_user"
    GET_USER_DATA = "get_user_data"
    DELETE_USER = "delete_user"


u_reg = pint.UnitRegistry()