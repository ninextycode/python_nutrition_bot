from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CallbackQueryHandler, filters
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler
from chatbot.config import secret
from chatbot.new_user import get_new_user_conversation_handler
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

import database


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def user_keyboard_markup():
    button_site = KeyboardButton(text="Web site 🌐")
    user_markup = ReplyKeyboardMarkup(
        [[button_site], ['📇', '📉', '💻']],
        resize_keyboard=True
    )

    return user_markup



sql_connection = database.open_connection()
database.use_database(sql_connection)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = f"Hello {update.effective_user.first_name}\n"
    await update.message.reply_text(message)

    id = update.effective_user.id
    user = database.select_user_by_id(sql_connection, id)
    if user is None:
        user_data = new_user_sequence()
        create_new_user(update.effective_user)
        message += "Created new user\n"
    message += "Awaiting registration\n"
    await update.message.reply_text(message)


def new_user_sequence(update: Update):
    dob = ask_date_of_birth(update)


async def ask_date_of_birth(update, context):
    await update.message.reply_text("Enter your date of birth (DD/MM/YYYY)")



async def ask_weight():
    pass


async def ask_activity_rate():
    pass


async def ask_weight_goals():
    pass



def create_new_user(effective_user):
    database.create_new_user(
        sql_connection, effective_user.first_name, effective_user.id,
        time_zone=None
    )



async def start_inline_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    # Get user that sent /start and log his name
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    # Build InlineKeyboard where each button has a displayed text
    # and a string as callback_data
    # The keyboard is a list of button rows, where each row is in turn
    # a list (hence `[[...]]`).
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="ONE"),
            InlineKeyboardButton("2", callback_data="TWO"),
        ]
    ]
    reply_markup = user_keyboard_markup()  # InlineKeyboardMarkup(keyboard)
    # Send message with text and appended InlineKeyboard
    await update.message.reply_text("Start handler, Choose a route", reply_markup=reply_markup)
    # Tell ConversationHandler that we're in state `FIRST` now
    return 0


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()
    await query.edit_message_text(text=f"Selected option: {query.data}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays info on how to use the bot."""
    await update.message.reply_text("Use /start to test this bot.")


def run_bot():
    app = ApplicationBuilder().token(secret).build()

    # app.add_handler(CommandHandler("start", start))

    new_user_handler =get_new_user_conversation_handler()

    app.add_handler(new_user_handler)

    # Run the bot until the user presses Ctrl-C
    app.run_polling(allowed_updates=Update.ALL_TYPES)
    app.run_polling()

