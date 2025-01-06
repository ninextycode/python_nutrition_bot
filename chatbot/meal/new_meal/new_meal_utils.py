from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.food_database_model import User, UserTarget
from database.select import select_meals
from database.common_sql import get_session
from enum import Enum, auto
import telegram.error
import logging
import io
from ai_interface.openai_meal_chat import ImageData
from pathlib import Path
from chatbot import dialog_utils
from ai_interface import openai_meal_chat
from database.food_database_model import (
    MealEaten, NutritionType
)

logger = logging.getLogger(__name__)


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
    MORE_INFO = "More info"
    REENTER_MANUALLY = "Re-enter manually"
    CANCEL = "Cancel"


class ConfirmManualOption(Enum):
    CONFIRM = "Confirm"
    REENTER = "Re-enter"
    CANCEL = "Cancel"


class OneMultipleIngredients(Enum):
    ONE = "Single meal entry"
    MULTIPLE = "Multiple ingredients"


class MoreIngredientsOrFinish(Enum):
    MORE = "Add more"
    FINISH = "Finish"


def assign_nutrition_values_from_dict(meal, nutrition_dict):
    meal.fat = nutrition_dict[NutritionType.FAT]
    meal.carbs = nutrition_dict[NutritionType.CARBS]
    meal.protein = nutrition_dict[NutritionType.PROTEIN]
    meal.calories = nutrition_dict[NutritionType.CALORIES]
    meal.weight = nutrition_dict[NutritionType.WEIGHT]


class KeepUpdateOption(Enum):
    UPDATE = "Enter new values"
    KEEP = "Keep existing"


class MealDataEntry(Enum):
    USER = auto()

    IS_USING_AI = auto()
    IMAGE_DATA_FOR_AI = auto()
    DESCRIPTION_FOR_AI = auto()
    LAST_AI_MESSAGE_LIST = auto()

    INGREDIENT_NUTRITION_DATA = auto()

    NEW_MEAL_OBJECT = auto()
    SAVE_FOR_FUTURE_USE = auto()

    LAST_SKIP_BUTTON_ID = "last_skip_button_id"


class InlineKeyData(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    IMAGE_DATA_FOR_AI = auto()
    DESCRIPTION_FOR_AI = auto()
    SKIP_SAVING_FOR_FUTURE_USE = auto()


def ai_manual_markup():
    keys = [v.value for v in InputMode]
    keys_layout = [
        [KeyboardButton(v) for v in keys[:2]],
        [KeyboardButton(v) for v in keys[2:]],
    ]
    return ReplyKeyboardMarkup(
        keys_layout, resize_keyboard=True
    )


async def input_mode_question(update):
    await update.message.reply_text(
        "First, I need you to choose input mode",
        reply_markup=ai_manual_markup()
    )



async def ai_input_question(update):
    await update.message.reply_text(
        "Using AI to determine nutrition.\n"
        "Describe your meal. It is helpful to specify the weight.\n"
        "Optionally, attach one picture.",
        reply_markup=ReplyKeyboardRemove()
    )


async def ask_for_image(update, meal_dialog_data):
    message_obj = await update.effective_message.reply_text(
        "Add an image",
        reply_markup=inline_button_markup("skip", InlineKeyData.IMAGE_DATA_FOR_AI.value)
    )
    meal_dialog_data[MealDataEntry.LAST_SKIP_BUTTON_ID] = (message_obj.chat.id, message_obj.id)


async def ask_for_description(update, meal_dialog_data):
    message_obj = await update.effective_message.reply_text(
        "Type your description",
        reply_markup=inline_button_markup("skip", InlineKeyData.DESCRIPTION_FOR_AI.value)
    )
    meal_dialog_data[MealDataEntry.LAST_SKIP_BUTTON_ID] = (message_obj.chat.id, message_obj.id)


async def remove_last_skip_button(context, meal_dialog_data):
    # AI data request messages have an inline keyboard with one button
    # that gives an option to skip
    # This button should be removed when it is no longer meaningful
    # (when data was provided, input was cancelled, etc.)
    if MealDataEntry.LAST_SKIP_BUTTON_ID not in meal_dialog_data:
        return

    chat_id, message_id = meal_dialog_data.pop(MealDataEntry.LAST_SKIP_BUTTON_ID)
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=message_id, reply_markup=None
        )
    except telegram.error.BadRequest as e:
        dialog_utils.pass_exception_if_message_not_modified(e)


def inline_button_markup(text, data_field_to_skip):
    return InlineKeyboardMarkup([[InlineKeyboardButton(
        text, callback_data=data_field_to_skip
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


async def ask_to_confirm_existing_description(update, meal_dialog_data):
    meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]
    name = meal.name
    description = meal.description

    message = (
        f"Name: {name}\n"
        f"Description: {description}\n"
        "Enter new name and description?"
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


async def ask_to_confirm_existing_nutrition(update, meal_dialog_data):
    message = (
        f"Nutrition data:\n" +
        nutrition_data_four_lines(meal_dialog_data) + "\n" +
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


async def ask_for_next_ingredient(update, meal_dialog_data):
    n_ingredients = len(meal_dialog_data.get(MealDataEntry.INGREDIENT_NUTRITION_DATA, []))
    new_ingredient_ord = n_ingredients + 1
    await update.message.reply_text(
        f"Ingredient {new_ingredient_ord}:",
        reply_markup=ReplyKeyboardRemove()
    )


def one_line_nutrition_format():
    nutrition_types_order = [t.value for t in NutritionType]

    nutrition_format_parts = []
    for i, nutrition in enumerate(nutrition_types_order):
        nutrition_format_parts.append(nutrition)
    return " / ".join(nutrition_format_parts)


async def ask_to_confirm_ai_estimate(update, meal_dialog_data, show_estimates=True):
    estimates = (
        "AI nutrition value estimate: \n" +
        meal_data_to_string(meal_dialog_data)
    )
    question = "Confirm data?"

    if show_estimates:
        message = estimates + "\n" + question
    else:
        message = question

    warning = get_warning_if_calories_exceeded(meal_dialog_data)
    if warning is not None:
        message = message + "\n\n" + warning

    # need to use update.effective_message
    # choosing to skip description or image input for AI
    # will make update.message None
    await update.effective_message.reply_text(
        message, reply_markup=confirm_ai_markup()
    )


def confirm_ai_markup():
    keys = [o.value for o in ConfirmAiOption]
    keys_layout = [
        [KeyboardButton(v) for v in keys[:2]],
        [KeyboardButton(v) for v in keys[2:]],
    ]
    return ReplyKeyboardMarkup(
        keys_layout, resize_keyboard=True
    )


async def ask_to_confirm_manual_entry_data(update, meal_dialog_data, long_nutrition=False):
    message = (
        meal_data_to_string(meal_dialog_data, long_nutrition) + "\n" +
        "Confirm data?"
    )

    warning = get_warning_if_calories_exceeded(meal_dialog_data)
    if warning is not None:
        message = message + "\n\n" + warning

    await update.message.reply_text(
        message, reply_markup=confirm_data_markup()
    )

def get_warning_if_calories_exceeded(meal_dialog_data):
    total_calories, calories_target = get_calories_check_values(meal_dialog_data)
    user: User = meal_dialog_data[MealDataEntry.USER]
    print(user.user_target_obj.target_type, total_calories, calories_target)
    if (
        user.user_target_obj.target_type == UserTarget.Type.MAXIMUM.value and
        total_calories > calories_target
    ):
        return f"Warning: calories exceeded ({total_calories:.0f} > {calories_target:.0f})"
    else:
        return None

def get_calories_check_values(meal_dialog_data):
    user: User = meal_dialog_data[MealDataEntry.USER]
    new_meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]

    calories_target = user.user_target_obj.calories
    date = user.get_datetime_now().date()
    with get_session() as session:
        meals = select_meals.get_meals_for_one_day(session, date, user)
    total_calories = sum([float(m.calories) for m in meals]) + float(new_meal.calories)
    return total_calories, calories_target


async def describe_ingredients(update, meal_dialog_data, include_total=False):
    named_ingredients = meal_dialog_data.get(MealDataEntry.INGREDIENT_NUTRITION_DATA, [])
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


def combine_ingredients(meal_dialog_data):
    named_ingredients = meal_dialog_data.pop(MealDataEntry.INGREDIENT_NUTRITION_DATA, [])
    names = [name for (name, nut) in named_ingredients if name is not None]
    nutrition_added = add_ingredients_nutrition(
        [nut for (name, nut) in named_ingredients]
    )

    meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]
    assign_nutrition_values_from_dict(meal, nutrition_added)

    if len(names) > 0:
        description = meal.description

        if len(description) > 0:
            description = description + "\n"

        description = description + "Ingredients: " + ", ".join(names)
        meal.description = description


def add_ingredients_nutrition(ingredients):
    nutrition_full = {k: 0 for k in NutritionType}
    for nut_vals in ingredients:
        for k, v in nut_vals.items():
            nutrition_full[k] = nutrition_full.get(k, 0) + v
    return nutrition_full


def confirm_data_markup():
    keys = [o.value for o in ConfirmManualOption]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v) for v in keys]], resize_keyboard=True
    )


def meal_data_to_string(meal_dialog_data, long_nutrition=False):
    if long_nutrition:
        nutrition_lines = nutrition_data_four_lines(meal_dialog_data, " - ")
    else:
        nutrition_lines = nutrition_data_two_lines(meal_dialog_data)

    meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]

    s = (
        f"Name: {meal.name}\n" +
        f"Description: {meal.description}\n" +
        nutrition_lines
    )
    return s


def nutrition_data_four_lines(meal_dialog_data, prefix=""):
    meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]
    nutrition_data = meal.nutrition_as_dict()
    macros = [
        NutritionType.CALORIES,
        NutritionType.FAT,
        NutritionType.PROTEIN
    ]

    nutrition_strings = []
    for nutrition_type in NutritionType:
        nutrition_val = nutrition_data[nutrition_type]
        nutrition_val_string = float_val_to_string(nutrition_val)
        nutrition_string = (
            prefix + nutrition_type.value + ": " + nutrition_val_string + nutrition_type.unit()
        )
        nutrition_strings.append(nutrition_string)

    total_grams_macros = sum([nutrition_data[n] for n in macros])
    percentage_strings = []
    for n in NutritionType:
        nutrition_val = nutrition_data[n]
        percentage_string = ""
        if n in macros:
            if total_grams_macros > 0:
                percentage = 100 * nutrition_val / total_grams_macros
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


def nutrition_data_two_lines(meal_dialog_data):
    meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]
    print("meal", meal)
    nutrition_data = meal.nutrition_as_dict()
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
    extension = Path(image_info.file_path).suffix[1:]
    with io.BytesIO() as bytes_io:
        await image_info.download_to_memory(bytes_io)
        bytes_io.seek(0)
        image_bytes = bytes_io.read()
    return ImageData(image_data=image_bytes, extension=extension)


async def ask_for_mode_information(update):
    await update.message.reply_text(
        "Type an extra message with additional information about the meal.",
        reply_markup=ReplyKeyboardRemove()
    )


async def handle_new_ai_response(ai_response, update, meal_dialog_data):
    ai_meal_data: openai_meal_chat.MealDataOutputFormat = ai_response.meal_data
    if not ai_meal_data.success_flag:
        await dialog_utils.no_markup_message(
            update, f"OpenAI error message: \n{ai_meal_data.error_message}"
        )
        return False

    meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]

    print("ai_meal_data", ai_meal_data)

    meal.carbs = ai_meal_data.carbohydrate
    meal.fat = ai_meal_data.fat
    meal.protein = ai_meal_data.protein
    meal.calories = ai_meal_data.calories
    meal.weight = ai_meal_data.total_weight
    meal.name = ai_meal_data.name
    meal.description = ai_meal_data.description

    meal_dialog_data[MealDataEntry.LAST_AI_MESSAGE_LIST] = openai_meal_chat.remove_non_text_messages(
        ai_response.message_list
    )
    return True


async def ask_to_save_meal_for_future_use(update):
    message = "Save meal for future use?"
    await update.message.reply_text(
        message, reply_markup=dialog_utils.yes_no_markup()
    )


async def ask_for_positive_weight(update, meal_dialog_data):
    message = (
        "To save data for future use, weight must be positive.\n"
        "Please enter a new meal weight value"
    )
    message_obj = await update.message.reply_text(
        message, reply_markup=inline_button_markup(
            "skip saving for future use", InlineKeyData.SKIP_SAVING_FOR_FUTURE_USE
        )
    )
    meal_dialog_data[MealDataEntry.LAST_SKIP_BUTTON_ID] = (message_obj.chat.id, message_obj.id)
