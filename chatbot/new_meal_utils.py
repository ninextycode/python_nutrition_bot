from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from enum import Enum, auto
import re
import telegram.error
import logging
import io
from ai_interface.openai_meal_chat import ImageData
from pathlib import Path
from chatbot import dialog_utils
from ai_interface import openai_meal_chat

logger = logging.getLogger(__name__)


LAST_SKIP_BUTTON_ID = "last_skip_button_id"
MEAL_DATA = "MEAL_DATA"


class InputMode(Enum):
    AI = "Use AI"
    MANUAL = "Text"
    BARCODE = "Barcode"
    HISTORY = "Saved meals"


class HandleAiErrorOption(Enum):
    START_AGAIN = "Try again"
    CANCEL = "Cancel"


class ConfirmAiOption(Enum):
    CONFIRM = "Confirm"
    START_AGAIN = "Try again"
    MORE_INFO = "Provide more details"
    REENTER_MANUALLY = "Re-enter manually"
    CANCEL = "Cancel"


class ConfirmManualOption(Enum):
    CONFIRM = "Confirm"
    REENTER = "Re-enter"
    CANCEL = "Cancel"


class OneMultipleIngredients(Enum):
    ONE = "One entry"
    MULTIPLE = "Multiple ingredients"


class MoreIngredientsOrFinish(Enum):
    MORE = "Add more"
    FINISH = "Finish"


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


class MealDataEntry(Enum):
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
    INGREDIENT_NUTRITION_DATA = auto()
    LAST_AI_MESSAGE_LIST = auto()


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
        reply_markup=skip_button_markup(MealDataEntry.IMAGE_DATA_FOR_AI.value)
    )
    if data_dict:
        data_dict[LAST_SKIP_BUTTON_ID] = (message.chat.id, message.id)


async def ask_for_description(update, data_dict=None):
    message = await update.effective_message.reply_text(
        "Type your description",
        reply_markup=skip_button_markup(MealDataEntry.DESCRIPTION_FOR_AI.value)
    )
    if data_dict:
        data_dict[LAST_SKIP_BUTTON_ID] = (message.chat.id, message.id)


async def remove_last_skip_button(context, user_data):
    # AI data request messages have an inline keyboard with one button
    # that gives an option to skip
    # This button should be removed when it is no longer meaningful
    # (when data was provided, input was cancelled, etc)
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
    name = meal_data[MealDataEntry.MEAL_NAME]
    description = meal_data.get(
        MealDataEntry.MEAL_DESCRIPTION, ""
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
        nutrition_data_four_lines(meal_data) + "\n" +
        "Enter new values?"
    )
    await update.message.reply_text(
        message, reply_markup=keep_update_markup()
    )


async def ask_one_or_many_ingredients_to_enter(update):
    message = "Specify as a single entry or as multiple ingredients?"
    await update.message.reply_text(
        message, reply_markup=one_multiple_markup()
    )


def one_multiple_markup():
    keys = [o.value for o in OneMultipleIngredients]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v) for v in keys]], resize_keyboard=True
    )


async def ask_more_ingredients_or_finish(update):
    message = "Add more or finish?"
    await update.message.reply_text(
        message, reply_markup=add_finish_markup()
    )


def add_finish_markup():
    keys = [o.value for o in MoreIngredientsOrFinish]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v) for v in keys]], resize_keyboard=True,
        one_time_keyboard=True
    )


async def ask_for_single_entry_nutrition(update, format_only=False):
    request_line = "Specify nutrition in a text message."
    format_message = (
        "Use the following format:\n" +
        one_line_nutrition_format()
    )
    if format_only:
        message = format_message
    else:
        message = request_line + "\n" + format_message
    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardRemove()
    )


async def ask_for_multiple_ingredients_nutrition(update, format_only=False):
    request_line = "Specify nutrition for each of the ingredients."
    format_message = (
        "Use the following format:\n" +
        "Name (optional)\n" +
        one_line_nutrition_format()
    )
    if format_only:
        message = format_message
    else:
        message = request_line + "\n" + format_message
    await update.message.reply_text(
        message, reply_markup=ReplyKeyboardRemove()
    )


async def ask_for_next_ingredient(update, meal_data):
    n_ingredients = len(meal_data.get(MealDataEntry.INGREDIENT_NUTRITION_DATA, []))
    new_ingredient_ord = n_ingredients + 1
    await update.message.reply_text(
        f"Ingredient {new_ingredient_ord}:",
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


async def ask_to_confirm_ai_estimate(update, meal_data):
    message = (
        "AI nutrition value estimate: \n" +
        meal_data_to_string(meal_data) + "\n" +
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


async def describe_ingredients(update, meal_data, include_total=False):
    named_ingredients = meal_data.get(MealDataEntry.INGREDIENT_NUTRITION_DATA, [])
    message_lines = ["Ingredients: " + one_line_nutrition_format()]
    for pos, (name, nut) in enumerate(named_ingredients, start=1):
        line = f"{pos}) "
        if name is not None:
            line += name + " : "
        line += nutrition_dict_to_str(nut)
        message_lines.append(line)

    if include_total:
        message_lines.append("")
        total_nut_value = add_ingredients_nutrition([
            nut for (name, nut) in named_ingredients
        ])
        total_line = "Total: " + nutrition_dict_to_str(total_nut_value)
        message_lines.append(total_line)

    message = "\n".join(message_lines)
    await update.message.reply_text(
        message, reply_markup=ReplyKeyboardRemove()
    )


def combine_ingredients(meal_data):
    named_ingredients = meal_data.pop(MealDataEntry.INGREDIENT_NUTRITION_DATA, [])
    names = [name for (name, nut) in named_ingredients if name is not None]
    nutrition_added = add_ingredients_nutrition(
        [nut for (name, nut) in named_ingredients]
    )

    meal_data[MealDataEntry.NUTRITION_DATA] = nutrition_added

    if len(names) > 0:
        description = meal_data.get(MealDataEntry.MEAL_DESCRIPTION, "")
        if len(description) > 0:
            description = description + "\n"
        description = description + "Ingredients: " + ", ".join(names)
        meal_data[MealDataEntry.MEAL_DESCRIPTION] = description


def add_ingredients_nutrition(ingredients):
    nutrition_full = {}
    for nut_vals in ingredients:
        for k, v in nut_vals.items():
            nutrition_full[k] = nutrition_full.get(k, 0) + v
    return nutrition_full


def confirm_data_markup():
    keys = [o.value for o in ConfirmManualOption]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v) for v in keys]], resize_keyboard=True
    )


def meal_data_to_string(meal_data, long_nutrition=False):
    if long_nutrition:
        nutrition_lines = nutrition_data_four_lines(meal_data, " - ")
    else:
        nutrition_lines = nutrition_data_two_lines(meal_data)

    s = (
        f"Name: {meal_data[MealDataEntry.MEAL_NAME]}\n" +
        f"Description: {meal_data[MealDataEntry.MEAL_DESCRIPTION]}\n" +
        nutrition_lines
    )
    return s


def nutrition_data_four_lines(meal_data, prefix=""):
    nutrition_data = meal_data[MealDataEntry.NUTRITION_DATA]
    nutrition_strings = []
    for n in NutritionType:
        nutrition_val = nutrition_data[n]
        nutrition_val_string = float_val_to_string(nutrition_val)
        nutrition_string = (
            prefix + n.value + ": " + nutrition_val_string + n.unit()
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
            final_lines.append(nutrition_s + f" ({percentage_s})")
        else:
            final_lines.append(nutrition_s)

    return "\n".join(final_lines)


def nutrition_data_two_lines(meal_data):
    nutrition_data = meal_data[MealDataEntry.NUTRITION_DATA]
    nutrition_format = one_line_nutrition_format()
    nutrition_string = nutrition_dict_to_str(nutrition_data)
    return nutrition_format + "\n" + nutrition_string


def nutrition_dict_to_str(nutrition_dict):
    nutrition_string = " / ".join([
        float_val_to_string(nutrition_dict.get(n, 0)) + n.unit()
        for n in NutritionType
    ])
    return nutrition_string


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


async def ask_for_mode_information(update):
    await update.message.reply_text(
        "Type an extra message with additional information about the meal.",
        reply_markup=ReplyKeyboardRemove()
    )


async def handle_new_ai_response(ai_response, update, meal_data):
    ai_meal_data = ai_response.meal_data
    if not ai_meal_data.success_flag:
        await dialog_utils.no_markup_message(
            update, f"OpenAI error message: \n{ai_meal_data.error_message}"
        )
        return False

    nutrition_data = {
        NutritionType.CALORIES: ai_meal_data.energy,
        NutritionType.CARB: ai_meal_data.carbohydrates,
        NutritionType.FATS: ai_meal_data.fats,
        NutritionType.PROTEINS: ai_meal_data.proteins,
    }
    meal_data[MealDataEntry.MEAL_NAME] = ai_meal_data.name
    meal_data[MealDataEntry.MEAL_DESCRIPTION] = ai_meal_data.description
    meal_data[MealDataEntry.NUTRITION_DATA] = nutrition_data
    meal_data[MealDataEntry.LAST_AI_MESSAGE_LIST] = openai_meal_chat.remove_non_text_messages(
        ai_response.message_list
    )
    return True


async def ask_to_save_meal_for_future_use(update):
    message = "Save meal for future use?"
    await update.message.reply_text(
        message, reply_markup=dialog_utils.yes_no_markup()
    )
