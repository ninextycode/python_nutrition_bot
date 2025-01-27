from telegram import (
    ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, Update
)
from database.food_database_model import NutritionType
from chatbot.config import Commands
from telegram.ext import ConversationHandler
from enum import Enum
import telegram.error
import re
from collections.abc import Iterable
from database import common_sql
from database.select import select_users


async def no_markup_message(update: Update, message, **kwargs):
    await update.effective_message.reply_text(
        message, reply_markup=ReplyKeyboardRemove(),
        **kwargs
    )


async def keep_markup_message(update: Update, message, **kwargs):
    # when one command creates a new dialog while another dialog exists
    # the "exit" message from the dialog that is about to end may destroy the markup
    # of the first message of the new dialog if it is created with "no_markup_message"
    # "keep_markyp_message" should be used as an alternative
    await update.effective_message.reply_text(
        message, **kwargs
    )


async def wrong_value_message(update: Update, extra_message=None):
    message = "Wrong value"
    if extra_message is not None:
        message = message + "\n" + extra_message

    await no_markup_message(update, message)


async def user_does_not_exist_message(update: Update):
    response = "User does not exist. "
    response += f"Use /{Commands.NEW_USER.value} instead"
    await no_markup_message(update, response)
    return ConversationHandler.END


class YesNo(Enum):
    YES = "Yes"
    NO = "No"


def yes_no_markup():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v.value) for v in YesNo]],
        resize_keyboard=True
    )


def yes_no_inline_markup():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(v.value) for v in YesNo]]
    )


async def handle_inline_keyboard_callback(update, delete_keyboard=False):
    await update.callback_query.answer()
    if delete_keyboard:
        try:
            await update.callback_query.edit_message_reply_markup(None)
        except telegram.error.BadRequest as e:
            pass_exception_if_message_not_modified(e)


async def delete_inline_keyboard(context, message_id, chat_id):
    await edit_message(
        context, chat_id, message_id, reply_markup=None
    )


async def edit_message(context, message_id, chat_id, text=None, reply_markup=None):
    try:
        if text is not None:
            await context.bot.edit_message_text(
                text, reply_markup=reply_markup,
                chat_id=chat_id, message_id=message_id
            )
        else:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, reply_markup=reply_markup
            )
    except telegram.error.BadRequest as e:
        pass_exception_if_message_not_modified(e)


def pass_exception_if_message_not_modified(e):
    # telegram raises exception if no change is needed, can be ignored
    if (
        isinstance(e, telegram.error.BadRequest) and
        e.message.startswith("Message is not modified")
    ):
        pass
    else:
        raise


def parse_nutrition_message(text, nutrition_entries=NutritionType):
    blocks = text.split(",")
    values = []

    for block in blocks:
        block = block.strip()
        # allow users to skip nutrition entries, substitute None
        if len(block) == 0:
            values.append(None)
            continue

        try:
            value = float(block)
        except ValueError:
            return None

        values.append(value)

    while len(values) < len(nutrition_entries):
        values.append(None)

    data = {}
    for t, value in zip(nutrition_entries, values):
        if value is not None:
            data[t] = max(0, value)  # treat negative values like zeroes
        else:
            data[t] = None

    return data


def is_collection(obj):
    return isinstance(obj, Iterable) and not isinstance(obj, (str, bytes))


async def silent_cancel(update: Update, context):
    query = update.callback_query
    if query is not None:
        await query.answer()
    return ConversationHandler.END


def get_tg_user_obj(update: Update):
    if update.message is not None:
        tg_id = update.message.from_user.id
    elif update.callback_query is not None:
        tg_id = update.callback_query.from_user.id
    else:
        return None

    with common_sql.get_session() as session:
        user = select_users.select_user_by_telegram_id(
            session, tg_id
        )
    return user


class TextEnum(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name
