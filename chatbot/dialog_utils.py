from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from chatbot.config import Commands
from telegram.ext import ConversationHandler
from enum import Enum


async def no_markup_message(update, message):
    await update.effective_message.reply_text(
        message, reply_markup=ReplyKeyboardRemove()
    )


async def wrong_value_message(update, extra_message=None):
    message = "Wrong value"
    if extra_message is not None:
        message = message + "\n" + extra_message

    await no_markup_message(update, message)


async def user_does_not_exist_message(update):
    response = "User does not exists. "
    response += f"Use /{Commands.NEW_USER} instead"
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
