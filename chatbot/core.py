from telegram.ext import ApplicationBuilder, ContextTypes
from telegram.ext import CommandHandler
from chatbot import config
from chatbot.config import secret, Commands
from chatbot.user.new_user import get_new_user_conversation_handler
from chatbot.meal.new_meal.new_meal import get_new_meal_conversation_handler
from chatbot.meal.meals_dataview.meals_eaten_dataview import (
    get_meals_eaten_view_conversation_handler
)
from chatbot.user.existing_user import get_existing_user_data, delete_user
import logging
from itertools import count
import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

logger = logging.getLogger(__name__)


def run_bot():
    app = ApplicationBuilder().token(secret).build()
    # config.bot_info = asyncio.run(app.bot.get_me())

    # app.add_handler(CommandHandler("start", start))

    group_count = count(1)

    new_user_handler = get_new_user_conversation_handler()
    app.add_handler(new_user_handler, group=next(group_count))

    new_meal_handler = get_new_meal_conversation_handler()
    app.add_handler(new_meal_handler, group=next(group_count))

    view_meals_eaten_handler = get_meals_eaten_view_conversation_handler()
    app.add_handler(view_meals_eaten_handler, group=next(group_count))

    show_user_data_handler = CommandHandler(
        Commands.GET_USER_DATA, get_existing_user_data
    )
    app.add_handler(show_user_data_handler, group=next(group_count))

    delete_user_handler = CommandHandler(
        Commands.DELETE_USER, delete_user
    )
    app.add_handler(delete_user_handler, group=next(group_count))

    # Run the bot until the user presses Ctrl-C
    app.run_polling(allowed_updates=Update.ALL_TYPES)
