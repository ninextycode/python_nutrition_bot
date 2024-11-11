from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from enum import Enum, auto
import re
import telegram.error
import logging


logger = logging.getLogger(__name__)


class InputMode(Enum):
    AI = "Use AI"
    MANUAL = "Enter Manually"
    BARCODE = "Scan barcode"


class NutritionTags(Enum):
    CARBS = "carb"
    FAT = "fat"
    PROTEIN = "prot"
    CALORIES = "cal"


LAST_SKIP_BUTTON_ID = "last_skip_button_id"


class UserDataFields(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    NAME = auto()
    IS_USING_AI = auto()
    IMAGE_FILE = auto()
    DESCRIPTION_FOR_AI = auto()


nutrition_tags = [t.value for t in NutritionTags]


def ai_manual_markup():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v.value) for v in InputMode]],
        resize_keyboard=True
    )


async def input_mode_question(update):
    await update.message.reply_text(
        "Select input mode",
        reply_markup=ai_manual_markup()
    )


def parse_meal_message(text):
    lines = text.split("\n")

    data_lines = {}
    lines_indicators = list(nutrition_tags)
    data = {"name": lines[0]}
    for i, l in enumerate(lines[1:]):
        for li in lines_indicators:
            if li in l:
                data_lines[li] = l

    for k, l in data_lines.items():
        val = parse_float(l)
        if val is not None:
            data[k] = val

    for li in lines_indicators:
        if li not in data:
            data[li] = None

    return data


def parse_float(l):
    match_whole = re.search(r"\d+(?:[.,]?\d+)?", l)
    match_frac_only = re.search(r"[.,]\d+", l)
    if match_whole is not None:
        return float(match_whole[0])
    elif match_frac_only is not None:
        return float(match_frac_only[0])
    else:
        return None


async def ai_input_question(update):
    await update.message.reply_text(
        "Using AI to determine nutrition.\n"
        "Describe your meal. It is helpful to specify the weight.\n"
        "Optionally, attach one picture.",
        reply_markup=ReplyKeyboardRemove()
    )


async def ask_for_picture(update, user_data_dict=None):
    message = await update.effective_message.reply_text(
        "Add an image",
        reply_markup=skip_button_markup(UserDataFields.IMAGE_FILE.value)
    )
    if user_data_dict:
        user_data_dict[LAST_SKIP_BUTTON_ID] = (message.chat.id, message.id)


async def ask_for_description(update, user_data_dict=None):
    message = await update.effective_message.reply_text(
        "Type your description",
        reply_markup=skip_button_markup(UserDataFields.DESCRIPTION_FOR_AI.value)
    )
    if user_data_dict:
        user_data_dict[LAST_SKIP_BUTTON_ID] = (message.chat.id, message.id)


async def remove_last_skip_button(context, user_data):
    if LAST_SKIP_BUTTON_ID not in user_data:
        return

    chat_id, message_id = user_data.pop(LAST_SKIP_BUTTON_ID)
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=message_id, reply_markup=None
        )
    except telegram.error.BadRequest as e:
        logger.warning("Exception handled: %s", e)


def skip_button_markup(data_field_to_skip):
    return InlineKeyboardMarkup([[InlineKeyboardButton(
        "skip", callback_data=data_field_to_skip
    )]])



