from telegram import (
    ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from database.food_database_model import NutritionType
from chatbot.config import Commands
from telegram.ext import ConversationHandler
from enum import Enum
import telegram.error
import re


async def no_markup_message(update, message, **kwargs):
    await update.effective_message.reply_text(
        message, reply_markup=ReplyKeyboardRemove(),
        **kwargs
    )


async def keep_markup_message(update, message, **kwargs):
    # when one command creates a new dialog while another dialog exists
    # the "exit" message from the dialog that is about to end may destroy the markup
    # of the first message of the new dialog if it is created with "no_markup_message"
    # "keep_markyp_message" should be used as an alternative
    await update.effective_message.reply_text(
        message, **kwargs
    )


async def wrong_value_message(update, extra_message=None):
    message = "Wrong value"
    if extra_message is not None:
        message = message + "\n" + extra_message

    await no_markup_message(update, message)


async def user_does_not_exist_message(update):
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
    separators = [" ", ",", "/", r"\n", r"\\", "|"]
    separators_merged = "".join(separators)
    blocks = [b for b in re.split(rf"[{separators_merged}]", text) if len(b) > 0]
    values = []

    for block in blocks:
        # allow users to skip nutrition entries, substitute zeros
        if len(block) == 0:
            values.append(0)
            continue

        try:
            value = float(block)
        except ValueError:
            return None

        values.append(value)

    while len(values) < len(nutrition_entries):
        values.append(0)

    data = {}
    for t, value in zip(nutrition_entries, values):
        data[t] = max(0, value)  # treat negative values like zeroes

    return data
