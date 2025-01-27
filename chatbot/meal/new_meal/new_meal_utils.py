from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from database.food_database_model import User, UserTarget
from database.select import select_meals
from database.common_sql import get_session
from ai_interface.openai_meal_chat import ImageData
from chatbot import dialog_utils
from chatbot.inline_key_utils import (
    InlineButtonDataValueGroup, InlineButtonDataKey, inline_keys_markup,
    StartConversationDataKey
)
from ai_interface import openai_meal_chat
from database.food_database_model import (
    MealEaten, NutritionType
)
from enum import Enum, auto
from pathlib import Path
import telegram.error
import logging
import io


logger = logging.getLogger(__name__)


class InputMode(Enum):
    AI = "Use AI"
    MANUAL = "Text"
    BARCODE = "Barcode"
    HISTORY = "Saved meals"


class EditMode(Enum):
    ADJUST_WITH_AI = "AI edit"
    MANUAL = "Manual edit"
    CHANGE_DATE_TIME = "Date & time"


class HandleAiErrorOption(Enum):
    START_AGAIN = "Try again"
    CANCEL = "Cancel"


class ConfirmAiOption(Enum):
    CONFIRM = "Confirm"
    MORE_INFO = "More info"
    REENTER_MANUALLY = "Edit manually"


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
    fat = nutrition_dict[NutritionType.FAT]
    meal.fat = first_not_none(fat, meal.fat, 0)

    carbs = nutrition_dict[NutritionType.CARBS]
    meal.carbs = first_not_none(carbs, meal.carbs, 0)

    protein = nutrition_dict[NutritionType.PROTEIN]
    meal.protein = first_not_none(protein, meal.protein, 0)

    calories = nutrition_dict[NutritionType.CALORIES]
    meal.calories = first_not_none(calories, meal.calories, 0)

    weight = nutrition_dict[NutritionType.WEIGHT]
    meal.weight = first_not_none(weight, meal.weight, 0)


def first_not_none(*args):
    for obj in args:
        if obj is not None:
            return obj


class KeepUpdateOption(Enum):
    UPDATE = "Enter new values"
    KEEP = "Keep existing"


class MealDataEntry(Enum):
    USER = auto()

    MEAL_DATE = auto()
    MEAL_TIME = auto()

    IMAGE_DATA_FOR_AI = auto()
    DESCRIPTION_FOR_AI = auto()
    LAST_AI_MESSAGE_LIST = auto()

    INGREDIENT_NUTRITION_DATA = auto()

    MEAL_OBJECT = auto()
    UPDATING_EXISTING = auto()
    SAVE_FOR_FUTURE_USE = auto()
    PARENT_ID = auto()

    LAST_SKIP_BUTTON_ID = auto()


def reset_ai_data(meal_dialog_data):
    meal_dialog_data.pop(MealDataEntry.IMAGE_DATA_FOR_AI, None)
    meal_dialog_data.pop(MealDataEntry.DESCRIPTION_FOR_AI, None)
    meal_dialog_data.pop(MealDataEntry.LAST_AI_MESSAGE_LIST, None)



class NewMealInlineDataKey(InlineButtonDataKey):
    SKIP_DESCRIPTION_FOR_AI = auto()
    SKIP_SAVING_FOR_FUTURE_USE = auto()
    CONFIRM_DATE_TIME = auto()


class ConfirmDateTimeBtnValue(InlineButtonDataValueGroup):
    @staticmethod
    def class_key():
        return NewMealInlineDataKey.CONFIRM_DATE_TIME
    CHANGE_DATE = auto()
    CHANGE_TIME = auto()
    CONFIRM = auto()


class SkipDescriptionBtnValue(InlineButtonDataValueGroup):
    @staticmethod
    def class_key():
        return NewMealInlineDataKey.SKIP_DESCRIPTION_FOR_AI
    IMAGE_DATA_FOR_AI = auto()
    DESCRIPTION_FOR_AI = auto()


def input_mode_markup():
    keys = [v.value for v in InputMode]
    keys_layout = [
        [KeyboardButton(v) for v in keys[:2]],
        [KeyboardButton(v) for v in keys[2:]],
    ]
    return ReplyKeyboardMarkup(
        keys_layout, resize_keyboard=True
    )


async def ask_input_mode(update):
    await update.effective_message.reply_text(
        "Please choose input mode",
        reply_markup=input_mode_markup()
    )


def edit_mode_markup():
    keys = [v.value for v in EditMode]
    keys_layout = [
        [KeyboardButton(v) for v in keys]
    ]
    return ReplyKeyboardMarkup(
        keys_layout, resize_keyboard=True
    )


async def ask_edit_mode(update):
    await update.effective_message.reply_text(
        "Please choose edit option",
        reply_markup=edit_mode_markup()
    )


async def ask_confirm_date_time(update, meal_dialog_data):
    date = meal_dialog_data[MealDataEntry.MEAL_DATE].strftime("%A %d %B %Y")
    time = meal_dialog_data[MealDataEntry.MEAL_TIME].strftime("%H:%M")
    await dialog_utils.no_markup_message(update, "Confirm meal date and time")
    message = (
        f"Date: {date}\n"
        f"Time: {time}\n"
    )
    markup = confirm_date_time_markup()
    await update.effective_message.reply_text(
        message, reply_markup=markup
    )


def confirm_date_time_markup():
    return inline_keys_markup(
        [f"Change date", f"Change time", f"Confirm"],
        [
            ConfirmDateTimeBtnValue.CHANGE_DATE.to_key_value_str(),
            ConfirmDateTimeBtnValue.CHANGE_TIME.to_key_value_str(),
            ConfirmDateTimeBtnValue.CONFIRM.to_key_value_str()
        ],
        n_btn_in_row=[2, 1]
    )


async def ask_date_of_meal(update):
    await dialog_utils.no_markup_message(
        update,
        "Please enter the date\n(Day/Month/Year)"
    )


async def ask_time_of_meal(update, date=None):
    if date is not None:
        date_lines = (
            "The date of the meal is \n" +
            date.strftime("%A %d %B %Y") + "\n\n"
        )
    else:
        date_lines = ""

    await dialog_utils.no_markup_message(
        update,
        (
            date_lines +
            "Please enter the time of the meal"
        )
    )


async def ask_ai_input(update):
    await update.message.reply_text(
        "Using AI to determine nutrition.\n"
        "Describe your meal. It is helpful to specify the weight.\n"
        "Optionally, attach one picture.",
        reply_markup=ReplyKeyboardRemove()
    )


async def ask_for_image(update, meal_dialog_data):
    message_obj = await update.effective_message.reply_text(
        "Add an image",
        reply_markup=inline_keys_markup("skip", SkipDescriptionBtnValue.IMAGE_DATA_FOR_AI.to_key_value_str())
    )
    meal_dialog_data[MealDataEntry.LAST_SKIP_BUTTON_ID] = (message_obj.chat.id, message_obj.id)


async def ask_for_description(update, meal_dialog_data):
    message_obj = await update.effective_message.reply_text(
        "Type your description",
        reply_markup=inline_keys_markup("skip", SkipDescriptionBtnValue.DESCRIPTION_FOR_AI.to_key_value_str())
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
    await dialog_utils.delete_inline_keyboard(
        context, chat_id, message_id
    )


async def ask_for_meal_description(update):
    message = (
        "Enter the name of the meal on the first line.\n"
        "Enter an optional description on the next line."
    )
    await update.message.reply_text(
        message, reply_markup=ReplyKeyboardRemove()
    )


async def ask_to_confirm_existing_description(update, meal: MealEaten):
    message = (
        "Meal data:\n" +
        meal.describe_no_nutrition(with_time=False)
    )
    await dialog_utils.no_markup_message(
        update, message
    )
    await ask_for_meal_description(update)
    await update.effective_message.reply_text(
        "Enter new values?", reply_markup=keep_update_markup()
    )

def keep_update_markup():
    keys = [o.value for o in KeepUpdateOption]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v) for v in keys]],
        resize_keyboard=True
    )


async def ask_to_confirm_existing_nutrition(update, meal_dialog_data):
    meal: MealEaten = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
    message = (
        f"Nutrition data:\n" +
        meal.describe_nutrition_only_long() + "\n"
    )
    await dialog_utils.no_markup_message(update, message)
    await ask_for_single_entry_nutrition(update)
    await update.effective_message.reply_text(
        "Enter new values?", reply_markup=keep_update_markup()
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
    return ", ".join(nutrition_format_parts)


async def ask_to_confirm_ai_estimate(update, meal, show_estimates=True):
    estimates = meal.describe()
    if show_estimates:
        await dialog_utils.no_markup_message(
            update, estimates
        )

    # need to use update.effective_message
    # choosing to skip description or image input for AI
    # will make update.message None
    await update.effective_message.reply_text(
        "Confirm data?", reply_markup=confirm_ai_markup()
    )


def confirm_ai_markup():
    keys = [o.value for o in ConfirmAiOption]
    keys_layout = [
        [KeyboardButton(v) for v in keys],
    ]
    return ReplyKeyboardMarkup(
        keys_layout, resize_keyboard=True
    )


async def ask_to_confirm_manual_entry_data(update, meal: MealEaten, long_nutrition=False):
    await dialog_utils.no_markup_message(
        update, meal.describe(long_format=long_nutrition)
    )
    await update.message.reply_text(
        "Confirm data?", reply_markup=confirm_data_markup()
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
    new_meal: MealEaten = meal_dialog_data[MealDataEntry.MEAL_OBJECT]

    calories_target = user.user_target_obj.calories
    if new_meal.created_local_datetime is None:
        date = user.get_datetime_now().date()
    else:
        date = new_meal.created_local_datetime.date()

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

    meal: MealEaten = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
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


def nutrition_data_two_lines(meal_dialog_data):
    meal: MealEaten = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
    nutrition_data = meal.nutrition_as_dict()
    nutrition_format = one_line_nutrition_format()
    nutrition_string = nutrition_dict_to_str(nutrition_data)
    return nutrition_format + "\n" + nutrition_string


def nutrition_dict_to_str(nutrition_dict):
    nutrition_string = ", ".join([
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


async def ask_for_more_information(update):
    await update.message.reply_text(
        "Send a message with additional information about the meal",
        reply_markup=ReplyKeyboardRemove()
    )


async def handle_new_ai_response(ai_response, update, meal_dialog_data):
    ai_meal_data: openai_meal_chat.MealDataOutput = ai_response.meal_data
    if not ai_meal_data.success_flag:
        await dialog_utils.no_markup_message(
            update, f"OpenAI error message: \n{ai_meal_data.error_message}"
        )
        return False

    meal: MealEaten = meal_dialog_data[MealDataEntry.MEAL_OBJECT]

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


def make_ai_message_list_from_meal(meal_dialog_data):
    meal = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
    meal_dialog_data[MealDataEntry.LAST_AI_MESSAGE_LIST] = \
        [openai_meal_chat.get_assistant_message_from_eaten_meal(meal)]


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
        message, reply_markup=inline_keys_markup(
            "skip saving for future use", NewMealInlineDataKey.SKIP_SAVING_FOR_FUTURE_USE.to_str()
        )
    )
    meal_dialog_data[MealDataEntry.LAST_SKIP_BUTTON_ID] = (message_obj.chat.id, message_obj.id)



async def new_meal_added_message(update, meal: MealEaten, view_meals_inline_btn=False):
    if view_meals_inline_btn:
        reply_markup = inline_keys_markup(
            "View meals",
            callback_data=StartConversationDataKey.VIEW_EATEN_MEALS.to_str()
        )
    else:
        reply_markup = ReplyKeyboardRemove()

    await dialog_utils.no_markup_message(
        update, meal.describe()
    )
    await update.message.reply_text(
        "New meal added", reply_markup=reply_markup
    )


async def meal_updated_message(update, meal: MealEaten, show_description=True):
    if show_description:
        await dialog_utils.no_markup_message(
            update, meal.describe()
        )
    await dialog_utils.no_markup_message(
        update, "Meal updated"
    )
