from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from database.food_database_model import ActivityLevelValue, MaleFemaleValue, User, UserTarget, NutritionType, GoalValue
from enum import Enum, auto
from chatbot import dialog_utils
from chatbot.config import u_reg, Commands
from ai_interface.mifflin_st_jeor import calculate_nutrition
import logging
import pint
import re
import datetime

logger = logging.getLogger(__name__)


class UpdateUserMode(Enum):
    NEW = auto()
    UPDATE = auto()


class UserDataEntry(Enum):
    NEW_USER_OBJECT = auto()
    OLD_USER_OBJECT = auto()
    IS_KETO = auto()


class MaleFemaleOption(Enum):
    MALE = "Male"
    FEMALE = "Female"


GoalOption = GoalValue


ActivityLevelOption = ActivityLevelValue


class ConfirmTargetOption(Enum):
    CONFIRM = "Confirm"
    CHOOSE_DIFFERENT = "Choose different"
    ENTER_MANUALLY = "Enter manually"


class TargetTypeOption(Enum):
    MAXIMUM = "Eat no more than the target"
    MINIMUM = "Eat at least as much as than the target"


new_value_query = "Enter new value"


async def ask_question(update, question, old_answers=None):
    if old_answers is not None:
        reply_markup = old_value_or_enter_new_markup(old_answers)
    else:
        reply_markup = ReplyKeyboardRemove()

    await update.message.reply_text(
        question, reply_markup=reply_markup
    )


def old_value_or_enter_new_markup(old_values=None):
    if old_values is None:
        old_values = []

    if not isinstance(old_values, (list, tuple)):
        old_values = [old_values]

    old_values = list(set(old_values))

    layout = [[f"{v}"] for v in old_values]
    layout.append([new_value_query])
    return ReplyKeyboardMarkup(
        layout, resize_keyboard=True
    )


async def ask_date_of_birth_question(update, old_date=None):
    if old_date is not None and isinstance(old_date, datetime.date):
        old_date = old_date.strftime("%d/%m/%Y")
    question = (
        "What is your date of birth? \n"
        "(Day/Month/Year)"
    )
    await ask_question(
        update, question, old_date
    )


async def ask_for_password(update):
    await update.message.reply_text(
        "Enter registration password", reply_markup=ReplyKeyboardRemove()
    )


async def ask_to_confirm_existing_name(update, existing_name):
    await update.message.reply_text(
        f"Hi {existing_name}! Let's set up a new user. \n" +
        "Is this your correct name?",
        reply_markup=dialog_utils.yes_no_markup(),
    )


async def ask_for_name(update, old_names=None):
    await ask_question(
        update, "Please enter your name", old_names
    )


async def ask_gender_question(update):
    await update.message.reply_text(
        "Please select your gender",
        reply_markup=male_female_markup()
    )


def male_female_markup():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(v.value) for v in MaleFemaleOption]],
        resize_keyboard=True
    )


async def ask_height_question(update, old_height=None):
    await ask_question(
        update, "What is your height?", old_height
    )


async def ask_weight_question(update, old_weight=None):
    await ask_question(
        update, "What is your weight? (kg unit assumed)", old_weight
    )


async def ask_goal_question(update):
    await update.message.reply_text(
        "What is your goal?",
        reply_markup=goal_markup()
    )


def goal_markup():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(g.value)]
            for g in GoalOption
        ],
        resize_keyboard=True
    )


async def ask_timezone_question(update, old_timezone=None):
    await update.message.reply_text(
        (
            "Let's determine your timezone.\n"
            "If you cannot send location, type and send your timezone name.\n"
            "Example: \"Europe/London\""
        ),
        reply_markup=location_markup(old_timezone)
    )


def location_markup(existing_values=None):
    keyboard_layout = []

    if existing_values is None:
        existing_values = []

    if not isinstance(existing_values, (list, tuple)):
        existing_values = [existing_values]

    if existing_values is not None:
        keyboard_layout.extend([[v] for v in existing_values])

    keyboard_layout.append(
        [KeyboardButton("Send location", request_location=True)]
    )

    return ReplyKeyboardMarkup(
        keyboard_layout,
        resize_keyboard=True
    )


def get_message_on_cancel(user_data):
    if user_data.get(UserDataEntry.OLD_USER_OBJECT, None) is None:
        command_type = "Registration"
        again_command = f"/{Commands.NEW_USER.value}"
    else:
        command_type = "Update"
        again_command = f"/{Commands.UPDATE_USER.value}"

    return (
        f"{command_type} cancelled. " +
        f"Use {again_command} command to start again!"
    )


def get_weight_kg(weight_str):
    weight_str = weight_str.lower()
    try:
        weight_with_unit = u_reg(weight_str)
        # assume units to be kilograms
        if not isinstance(weight_with_unit, pint.Quantity):
            weight_with_unit = weight_with_unit * u_reg("kg")
    except pint.PintError:
        return None

    weight_kg = weight_with_unit.to("kg").magnitude
    good_weight = 25 < weight_kg < 650

    if good_weight:
        return weight_kg
    else:
        return None


def get_height_cm(height_str):
    height_str = height_str.lower()

    feet_match = re.search(r"(\d+)'(\d+)?\"?", height_str)
    if feet_match:
        feet = feet_match.group(1)
        inches = feet_match.group(2) if feet_match.group(2) else "0"
        height_str = f"{feet} feet + {inches} inches "

    try:
        height_with_unit = u_reg(height_str)
    except pint.PintError:
        return None

    # deduce unit from the magnitude
    if not isinstance(height_with_unit, pint.Quantity):
        if height_with_unit < 3:
            height_with_unit = height_with_unit * u_reg("m")
        elif height_with_unit < 9:
            height_with_unit = height_with_unit * u_reg("ft")
        elif 90 < height_with_unit < 300:
            height_with_unit = height_with_unit * u_reg("cm")
        else:
            return None

    height_cm = height_with_unit.to("cm").magnitude
    good_height = 90 < height_cm < 300

    if good_height:
        return height_cm
    else:
        return None


async def ask_activity_level(update):
    question = "Choose your activity level"
    await update.message.reply_text(
        question, reply_markup=activity_level_markup()
    )


def activity_level_markup():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(g.value)]
            for g in ActivityLevelValue
        ],
        resize_keyboard=True
    )


async def ask_if_keto(update):
    question = "Keto diet?"
    await update.message.reply_text(
        question, reply_markup=dialog_utils.yes_no_markup()
    )


def assign_target_obj(dialog_data):
    user: User = dialog_data[UserDataEntry.NEW_USER_OBJECT]
    is_keto = dialog_data[UserDataEntry.IS_KETO]
    target_dict = calculate_nutrition(
        is_male=(user.gender_obj.gender == MaleFemaleValue.MALE.value),
        age=user.get_age(),
        height_cm=user.height,
        weight_kg=user.weight,
        activity_level=user.activity_level_obj.name,
        goal=user.goal_obj.goal,
        keto=is_keto
    )

    if user.goal_obj.goal in [GoalValue.GAIN_MUSCLE.value, GoalValue.GAIN_MUSCLE_SLOWLY.value]:
        target_type = "MINIMUM"
    else:
        target_type = "MAXIMUM"

    if user.user_target_obj is None:
        user.user_target_obj = UserTarget()

    target_obj = user.user_target_obj
    target_obj.calories = target_dict[NutritionType.CALORIES]
    target_obj.protein = target_dict[NutritionType.PROTEIN]
    target_obj.fat = target_dict[NutritionType.FAT]
    target_obj.carbs = target_dict[NutritionType.CARBS]
    target_obj.target_type = target_type


async def ask_to_confirm_target(update, user_target_obj: UserTarget):
    message = user_target_obj.describe()
    await dialog_utils.no_markup_message(update, message)
    question = "Confirm nutrition target?"
    await update.message.reply_text(
        question, reply_markup=confirm_target_markup()
    )


def confirm_target_markup():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(g.value) for g in ConfirmTargetOption]
        ],
        resize_keyboard=True
    )


async def ask_to_enter_target_manually(update):
    no_weight_keys = NutritionType.without_weight()
    nutrition_format_parts = []
    for i, nutrition in enumerate(no_weight_keys):
        nutrition_format_parts.append(nutrition)

    question = (
        "Enter nutrition target values.\n" +
        "Use the following format:\n" +
        " / ".join([n.value for n in nutrition_format_parts])
    )
    await dialog_utils.no_markup_message(update, question)


async def ask_target_type(update):
    question = "Choose nutrition target type"
    await update.message.reply_text(
        question, reply_markup=target_type_markup()
    )


def target_type_markup():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(g.value)]
            for g in TargetTypeOption
        ],
        resize_keyboard=True
    )
