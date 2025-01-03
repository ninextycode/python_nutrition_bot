from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from chatbot.config import Commands
from telegram.ext import ConversationHandler
from enum import Enum
import telegram.error


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


def pass_exception_if_message_not_modified(e):
    # telegram raises exception if no change is needed, can be ignored
    if (
        isinstance(e, telegram.error.BadRequest) and
        e.message.startswith("Message is not modified")
    ):
        pass
    else:
        raise
