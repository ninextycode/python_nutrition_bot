from database import common_sql
from database.select import select_users
from database.update import update_users
from chatbot.config import Commands
from chatbot import dialog_utils
from chatbot.user import user_utils
import logging


async def get_existing_user_data(update, context):
    tg_id = update.message.from_user.id

    with common_sql.get_session() as session:
        user = select_users.select_user_by_telegram_id(
            session, tg_id
        )

    if user is None:
        await dialog_utils.no_markup_message(
            update, f"User is missing. Use /{Commands.NEW_USER} command."
        )
        return

    message = user.describe()
    await dialog_utils.no_markup_message(update, message)
    return


async def delete_user(update, context):
    # todo only for testing
    tg_id = str(update.message.from_user.id)
    try:
        with common_sql.get_session() as session:
            success = update_users.delete_user_by_telegram_id(session, tg_id)

        if success:
            await dialog_utils.no_markup_message(
                update, f"User with telegram id {tg_id} deleted"
            )
        else:
            await dialog_utils.user_does_not_exist_message(update)
            await dialog_utils.no_markup_message(
                update, f"Telegram id = {tg_id}"
            )
    except Exception as e:
        logging.exception(e)
        await dialog_utils.no_markup_message(update, "Database error")

