import sqlalchemy as sa
from database.common_sql import get_session
from enum import Enum, auto
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.food_database_model import User, MealEaten, NutritionType
from database.select import select_meals
from chatbot import dialog_utils, config
from telegram.constants import ParseMode
import datetime
from typing import override
import telegram.error
import logging
from telegram import ReplyKeyboardRemove
import traceback


logger = logging.getLogger(__name__)
no_weight_nutrition_keys = [n for n in NutritionType if n != NutritionType.WEIGHT]
MEALS_EATEN_DB = "MEALS_EATEN_DB"


class MealsEatenViewDataEntry(Enum):
    USER_ID = auto()
    SINGLE_MEAL_ID = auto()
    USER_TIMEZONE = auto()
    DATE = auto()
    DATAVIEW_CHAT_ID_MESSAGE_ID = auto()


class TextEnum(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name


class InlineKeyDataPayload:
    def __init__(self, key, value=None):
        self.key = key.value if isinstance(key, Enum) else key
        self.value = str(value)

    @staticmethod
    def from_str(s: str):
        if " " in s:
            key, value = s.rsplit(" ", 1)
        else:
            key, value = s, None
        key = InlineKeyData[key].value
        return InlineKeyDataPayload(key, value)

    def to_str(self):
        if self.value is None:
            return self.key
        else:
            return self.key + " " + self.value


class InlineKeyData(TextEnum):
    SINGLE_MEAL_SELECTION = auto()
    ADD_MEAL = auto()
    DATE_NAVIGATION = auto()
    DELETE_MEAL = auto()
    EDIT_MEAL = auto()
    BACK_TO_DAY_VIEW = auto()

    def as_payload(self, value=None):
        return InlineKeyDataPayload(self, value)

    def as_payload_str(self, value=None):
        return self.as_payload(value).to_str()


class PayloadValueEnum(TextEnum):
    @staticmethod
    def get_payload_key():
        return None

    def as_payload(self):
        return InlineKeyDataPayload(
            self.__class__.get_payload_key(), self.value
        )

    def as_payload_str(self):
        return self.as_payload().to_str()


class DateNavigationOption(PayloadValueEnum):
    @staticmethod
    def get_payload_key():
        return InlineKeyData.DATE_NAVIGATION

    NEXT = auto()
    PREVIOUS = auto()
    ENTER_DATE = auto()


async def message_day_meals(update, context, update_existing):
    dialog_data = context.user_data[MEALS_EATEN_DB]

    date = dialog_data[MealsEatenViewDataEntry.DATE]

    with get_session() as session:
        meals = get_day_meals(session, date, dialog_data)

    nutrition_total = NutritionType.sum_nutrition_as_dict(meals)
    no_weight_keys = [n for n in NutritionType if n != NutritionType.WEIGHT]
    message = (
        date.strftime("%A %d %B %Y") + "\n"
        "      " + " / ".join([n.value for n in NutritionType if n != NutritionType.WEIGHT]) + "\n" +
        "Total: " + " / ".join([f"{nutrition_total[k]:.0f}" for k in no_weight_keys])
    )

    reply_markup = get_meals_inline_keyboard_markup(meals)

    await send_dataview_message(
        update, context, message, reply_markup,
        update_existing
    )


def get_meals_inline_keyboard_markup(meals: list[MealEaten]):
    buttons = []
    for meal in meals:
        meal_nutrition_dict = meal.nutrition_as_dict()
        message = (
            meal.name + "\n" +
            " / ".join([f"{meal_nutrition_dict[k]:.0f}" for k in no_weight_nutrition_keys])
        )

        buttons.append(
            InlineKeyboardButton(
                message, callback_data=InlineKeyData.SINGLE_MEAL_SELECTION.as_payload_str(meal.id)
            )
        )
    food_button_rows = [[b] for b in buttons]
    add_meal_button = [
        InlineKeyboardButton(
            "️Add a new meal", callback_data=InlineKeyData.ADD_MEAL.as_payload_str()
        )
    ]
    navigation_buttons = [
        InlineKeyboardButton(
            "◀", callback_data=DateNavigationOption.PREVIOUS.as_payload_str()
        ),
        InlineKeyboardButton(
            "Date", callback_data=DateNavigationOption.ENTER_DATE.as_payload_str()
        ),
        InlineKeyboardButton(
            "▶", callback_data=DateNavigationOption.NEXT.as_payload_str()
        ),
    ]
    # TODO no [add_meal_button] for now - add later
    button_rows = food_button_rows + [navigation_buttons]
    return InlineKeyboardMarkup(button_rows)


def get_day_meals(session, date, dialog_data):
    user_id = dialog_data[MealsEatenViewDataEntry.USER_ID]
    user_timezone = dialog_data[MealsEatenViewDataEntry.USER_TIMEZONE]

    if isinstance(date, datetime.datetime):
        date = date.date()

    start_day = datetime.datetime.combine(
        date, datetime.time(0, 0),
        tzinfo=user_timezone
    )
    one_day_offset = datetime.timedelta(days=1)
    next_day = start_day + one_day_offset
    meals_day = select_meals.select_meals_eaten_right_exclude_to(
        session, user_id, start_day, next_day
    )
    return meals_day


async def delete_dataview_message(context):
    dialog_data = context.user_data[MEALS_EATEN_DB]
    if MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID not in dialog_data:
        logger.warning("dataview message data does not exist, message cannot be deleted")
        return
    chat_id, message_id = dialog_data.pop(MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID)
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)


async def ask_for_date(update):
    question = (
        "Enter the date (Day/Month/Year) or \"today\" / \"yesterday\""
    )
    await dialog_utils.no_markup_message(update, question)


async def message_single_meal(update, context, meal_id, update_existing=True):
    with get_session() as session:
        meal = select_meals.select_meal_eaten_by_meal_id(session, meal_id)

    if meal is None:
        error_message = f"Meal with id {meal_id} does not exist"
        logger.error(error_message)
        raise ValueError(error_message)

    message = meal.describe()
    reply_markup = get_single_meal_inline_keyboard_markup()

    await send_dataview_message(update, context, message, reply_markup, update_existing)


def get_single_meal_inline_keyboard_markup():
    buttons = [
        [InlineKeyboardButton("Delete", callback_data=InlineKeyData.DELETE_MEAL.as_payload_str()),
         InlineKeyboardButton("Edit", callback_data=InlineKeyData.EDIT_MEAL.as_payload_str()),
         InlineKeyboardButton("Back", callback_data=InlineKeyData.BACK_TO_DAY_VIEW.as_payload_str())]
    ]
    return InlineKeyboardMarkup(buttons)


async def send_dataview_message(update, context, text, reply_markup, update_existing):
    dialog_data = context.user_data[MEALS_EATEN_DB]

    if update_existing and MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID in dialog_data:
        chat_id, message_id = dialog_data[MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID]
        try:
            await context.bot.edit_message_text(
                text, reply_markup=reply_markup,
                chat_id=chat_id, message_id=message_id
            )
        except telegram.error.BadRequest as e:
            dialog_utils.pass_exception_if_message_not_modified(e)
    else:
        message_obj = await update.message.reply_text(
            text, reply_markup=reply_markup
        )
        dialog_data[MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID] = (
            message_obj.chat.id, message_obj.id
        )
