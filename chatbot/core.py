from telegram.ext import ApplicationBuilder, ContextTypes
from telegram.ext import CommandHandler
from chatbot.config import secret, Commands, is_production
from chatbot.user.new_user_data import get_new_user_update_user_conv_handlers
from chatbot.start_menu.start_menu import get_start_menu_conversation_handler
from chatbot.meal.new_meal.new_meal_data import get_new_meal_conversation_handler
from chatbot.meal.meals_dataview.meals_eaten_dataview import (
    get_meals_eaten_view_conversation_handler
)
from chatbot.user.existing_user import get_existing_user_data, delete_user
from chatbot.user.birthday import get_birthday_handler
import logging
from itertools import count
from telegram import Update
from chatbot import dialog_utils
from telegram.warnings import PTBUserWarning
from warnings import filterwarnings

# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Frequently-Asked-Questions#what-do-the-per_-settings-in-conversationhandler-do
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)
logger = logging.getLogger(__name__)


async def start_handler(update, context):
    commands = [
        f"/{c.value}" for c in Commands
    ]
    message = "\n".join([
        "Available commands:",
        *commands
    ])
    await dialog_utils.no_markup_message(update, message)


def run_bot():
    app = ApplicationBuilder().token(secret).build()
    # config.bot_info = asyncio.run(app.bot.get_me())

    new_user_handler, update_user_handler = \
        get_new_user_update_user_conv_handlers()

    new_user_handlers = [
        new_user_handler
    ]

    new_meal_handler = get_new_meal_conversation_handler()
    view_meals_eaten_handler = get_meals_eaten_view_conversation_handler(
        new_meal_handler
    )
    show_user_data_handler = CommandHandler(
        Commands.GET_USER_DATA.value, get_existing_user_data
    )
    existing_user_handlers = [
        update_user_handler,
        new_meal_handler,
        view_meals_eaten_handler,
        show_user_data_handler
    ]


    start_dialog_handler = get_start_menu_conversation_handler(
        new_user_handlers,
        existing_user_handlers
    )

    all_conv_handlers = [start_dialog_handler] + \
        new_user_handlers + existing_user_handlers

    for conv_handler in all_conv_handlers:
        app.add_handler(conv_handler)



    #
    # app.add_handler(new_meal_handler, group=next(group_count))
    # app.add_handler(view_meals_eaten_handler, group=next(group_count))
    #
    # app.add_handler(show_user_data_handler, group=next(group_count))
    #
    # delete_user_handler = CommandHandler(
    #     Commands.DELETE_USER.value, delete_user
    # )
    # app.add_handler(delete_user_handler, group=next(group_count))

    birthday_handler = get_birthday_handler()
    app.add_handler(birthday_handler, group=next(group_count))

    logger.warning(
        f"starting telegram bot, is_production={is_production}"
    )
    # Run the bot until the user presses Ctrl-C
    app.run_polling(allowed_updates=Update.ALL_TYPES)
