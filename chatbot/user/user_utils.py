from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from database.food_database_model import User
import datetime
from enum import Enum, auto
from chatbot import dialog_utils
from chatbot.config import u_reg, Commands
import logging
import pint
import re

logger = logging.getLogger(__name__)
USER_DATA = "USER_DATA"


class UpdateUserMode(Enum):
    NEW = auto()
    UPDATE = auto()


class UserDataEntry(Enum):
    NEW_USER_OBJECT = auto()
    OLD_USER_OBJECT = auto()


class MaleFemaleOption(Enum):
    MALE = "Male"
    FEMALE = "Female"


class GoalOption(Enum):
    LOSE_WEIGHT = "lose weight"
    LOSE_WEIGHT_SLOWLY = "lose weight slowly"
    MAINTAIN_WEIGHT = "maintain weight"
    GAIN_MUSCLE_SLOWLY = "gain muscle slowly"
    GAIN_MUSCLE = "gain muscle"


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
    keyboard_layout = [
        [KeyboardButton("Send location", request_location=True)]
    ]

    if existing_values is None:
        existing_values = []

    if not isinstance(existing_values, (list, tuple)):
        existing_values = [existing_values]

    if existing_values is not None:
        keyboard_layout.extend([[v] for v in existing_values])

    return ReplyKeyboardMarkup(
        keyboard_layout,
        resize_keyboard=True
    )


async def send_message_on_cancel(update, user_data):
    if user_data.get(UserDataEntry.OLD_USER_OBJECT, None) is None:
        command_type = "Registration"
        again_command = f"/{Commands.NEW_USER}"
    else:
        command_type = "Update"
        again_command = f"/{Commands.UPDATE_USER}"

    await update.message.reply_text(
        f"{command_type} cancelled. " +
        f"Use {again_command} command to start again!",
        reply_markup=ReplyKeyboardRemove()
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
