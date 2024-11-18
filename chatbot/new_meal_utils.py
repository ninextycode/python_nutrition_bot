from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from enum import Enum, auto
import re
import telegram.error
import logging
import io
from ai_interface.openai_meal_chat import ImageData
from pathlib import Path

logger = logging.getLogger(__name__)


LAST_SKIP_BUTTON_ID = "last_skip_button_id"
MEAL_DATA = "MEAL_DATA"


class InputMode(Enum):
    AI = "Use AI"
    MANUAL = "Enter Manually"
    BARCODE = "Scan barcode"


class HandleAiErrorOption(Enum):
    START_AGAIN = "Try again"
    CANCEL = "Cancel"


class ConfirmAiOption(Enum):
    CONFIRM = "Confirm"
    START_AGAIN = "Try again"
    EXTRA_MESSAGE = "Provide more details"
    REENTER_MANUALLY = "Re-enter manually"
    CANCEL = "Cancel"


class ConfirmManualOption(Enum):
    CONFIRM = "Confirm"
    REENTER_MANUALLY = "Re-enter"
    CANCEL = "Cancel"


class NutritionType(Enum):
    CALORIES = "Calories"
    FATS = "Fats"
    CARB = "Carbs"
    PROTEINS = "Proteins"

    def unit(self):
        if self == NutritionType.CALORIES:
            return "kcal"
        else:
            return "g"


class KeepUpdateOption(Enum):
    UPDATE = "Enter new values"
    KEEP = "Keep existing"


class UserDataEntry(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    USER_NAME = auto()
    MEAL_NAME = auto()
    MEAL_DESCRIPTION = auto()
    IS_USING_AI = auto()
    IMAGE_DATA_FOR_AI = auto()
    DESCRIPTION_FOR_AI = auto()
    NUTRITION_DATA = auto()
    LAST_AI_RESPONSE = auto()


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


def parse_nutrition_message(text):
    separators = [" ", ",", "/", r"\n", r"\\", "|"]
    separators_merged = "".join(separators)
    blocks = re.split(rf"[{separators_merged}]", text)

    values = []

    for block in blocks:
        if len(block) == 0:
            values.append(0)
            continue

        value = parse_float(block)
        if value is not None:
            values.append(value)

    while len(values) < len(NutritionType):
        values.append(0)

    data = {}
    for t, value in zip(NutritionType, values):
        data[t] = value

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


async def ask_for_image(update, data_dict=None):
    message = await update.effective_message.reply_text(
        "Add an image",
        reply_markup=skip_button_markup(UserDataEntry.IMAGE_DATA_FOR_AI.value)
    )
    if data_dict:
        data_dict[LAST_SKIP_BUTTON_ID] = (message.chat.id, message.id)


async def ask_for_description(update, data_dict=None):
    message = await update.effective_message.reply_text(
        "Type your description",
        reply_markup=skip_button_markup(UserDataEntry.DESCRIPTION_FOR_AI.value)
    )
    if data_dict:
        data_dict[LAST_SKIP_BUTTON_ID] = (message.chat.id, message.id)


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


async def ask_for_meal_description(update):
    message = (
        "Enter the name of the meal on the first line.\n"
        "Enter an optional description on the next line."
    )
    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardRemove()
    )


async def ask_to_confirm_existing_description(update, meal_data):
    name = meal_data[UserDataEntry.MEAL_NAME]
    description = meal_data.get(
        UserDataEntry.MEAL_DESCRIPTION, ""
    )
    message = (
        f"Name: \"{name}\"\n"
        f"Description: \"{description}\"\n"
        "Enter new values?"
    )
    await update.message.reply_text(
        message, reply_markup=keep_update_markup()
    )


def keep_update_markup():
    keys = [o.value for o in KeepUpdateOption]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v) for v in keys]],
        resize_keyboard=True
    )


async def ask_to_confirm_existing_nutrition(update, meal_data):
    message = (
        f"Nutrition data:\n" +
        nutrition_data_4_lines(meal_data) + "\n" +
        "Enter new values?"
    )
    await update.message.reply_text(
        message, reply_markup=keep_update_markup()
    )


async def ask_for_nutrition_values(update):

    message = (
        "Specify nutrition manually.\n" +
        "Use the following format:\n" +
        one_line_nutrition_format()
    )
    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardRemove()
    )


def one_line_nutrition_format():
    nutrition_types_order = [t.value for t in NutritionType]
    units = [t.unit() for t in NutritionType]
    units_set = set(units)
    first_unit_positions = {}

    for unit in units_set:
        first_unit_positions[units.index(unit)] = unit

    nutrition_format_parts = []
    for i, nutrition in enumerate(nutrition_types_order):
        nutrition_format = nutrition
        if i in first_unit_positions.keys():
            nutrition_format += f" ({first_unit_positions[i]})"
        nutrition_format_parts.append(nutrition_format)
    return " / ".join(nutrition_format_parts)


async def ask_to_confirm_ai_estimate(update):
    message = (
        meal_data_to_string(update.user_data[MEAL_DATA]) + "\n" +
        "Confirm data?"
    )
    await update.message.reply_text(
        message, reply_markup=confirm_ai_markup()
    )


def confirm_ai_markup():
    keys = [o.value for o in ConfirmAiOption]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v) for v in keys]], resize_keyboard=True
    )


async def ask_to_confirm_manual_entry_data(update, meal_data, long_nutrition=False):
    message = (
        meal_data_to_string(meal_data, long_nutrition) + "\n" +
        "Confirm data?"
    )
    await update.message.reply_text(
        message, reply_markup=confirm_data_markup()
    )


def confirm_data_markup():
    keys = [o.value for o in ConfirmManualOption]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v) for v in keys]], resize_keyboard=True
    )


def meal_data_to_string(meal_data, long_nutrition=False):
    if long_nutrition:
        nutrition_lines = nutrition_data_4_lines(meal_data, " - ")
    else:
        nutrition_lines = nutrition_data_2_lines(meal_data)

    s = (
        f"Name: {meal_data[UserDataEntry.MEAL_NAME]}\n" +
        f"Description: {meal_data[UserDataEntry.MEAL_DESCRIPTION]}\n" +
        nutrition_lines
    )
    return s


def nutrition_data_4_lines(meal_data, prefix=""):
    nutrition_data = meal_data[UserDataEntry.NUTRITION_DATA]
    nutrition_strings = []
    for n in NutritionType:
        nutrition_val = nutrition_data[n]
        nutrition_val_string = float_val_to_string(nutrition_val)
        nutrition_string = (
            prefix + n.value + ": " + nutrition_val_string + " " + n.unit()
        )
        nutrition_strings.append(nutrition_string)

    grams = [nutrition_data[n] for n in NutritionType if n.unit().startswith("g")]
    total_grams = sum(grams)
    percentage_strings = []
    for n in NutritionType:
        nutrition_val = nutrition_data[n]
        percentage_string = ""
        if n.unit().startswith("g"):
            if total_grams > 0:
                percentage = 100 * nutrition_val / total_grams
            else:
                percentage = 0
            percentage_string = f"{percentage:.0f}%"
        percentage_strings.append(percentage_string)

    final_lines = []
    for nutrition_s, percentage_s in zip(nutrition_strings, percentage_strings):
        if len(percentage_s) > 0:
            final_lines.append(nutrition_s + " - " + percentage_s)
        else:
            final_lines.append(nutrition_s)

    return "\n".join(final_lines)


def nutrition_data_2_lines(meal_data):
    nutrition_data = meal_data[UserDataEntry.NUTRITION_DATA]
    nutrition_format = one_line_nutrition_format()
    nutrition_string = " / ".join([
        float_val_to_string(nutrition_data[n]) for n in NutritionType
    ])
    return nutrition_format + "\n" + nutrition_string


def float_val_to_string(val):
    val_string = f"{int(val) if val.is_integer() else val}"
    return val_string


async def telegram_photo_obj_to_image_data(photo_obj):
    image_info = await photo_obj.get_file()
    extension = Path(image_info.file_path).suffix
    with io.BytesIO() as bytes_io:
        await image_info.download_to_memory(bytes_io)
        image_bytes = bytes_io.read(0)
    return ImageData(image_data=image_bytes, extension=extension)
