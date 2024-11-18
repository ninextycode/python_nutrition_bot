from telegram.ext import ApplicationBuilder, ContextTypes
from telegram.ext import CommandHandler
from chatbot.config import secret, Commands
from chatbot.new_user import get_new_user_conversation_handler
from chatbot.new_meal import get_new_meal_conversation_handler
from chatbot.existing_user import get_existing_user_data, delete_user
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

logger = logging.getLogger(__name__)


def run_bot():
    app = ApplicationBuilder().token(secret).build()

    # app.add_handler(CommandHandler("start", start))

    new_user_handler = get_new_user_conversation_handler()
    app.add_handler(new_user_handler, group=2)

    new_meal_handler = get_new_meal_conversation_handler()
    app.add_handler(new_meal_handler, group=1)

    show_user_data_handler = CommandHandler(
        Commands.GET_USER_DATA, get_existing_user_data
    )
    app.add_handler(show_user_data_handler, group=3)

    delete_user_handler = CommandHandler(
        Commands.DELETE_USER, delete_user
    )
    app.add_handler(delete_user_handler, group=4)

    # Run the bot until the user presses Ctrl-C
    app.run_polling(allowed_updates=Update.ALL_TYPES)
    app.run_polling()

