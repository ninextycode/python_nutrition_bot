import datetime

from database.common_sql import get_session
from enum import Enum, auto
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.food_database_model import MealEaten, NutritionType
from database.select import select_meals
from chatbot import dialog_utils
from chatbot.config import DataKeys
import telegram.error
import logging
from chatbot import inline_key_utils
from chatbot.inline_key_utils import (
    InlineButtonDataKey, InlineButtonDataValueGroup, StartConversationDataKey
)
from chatbot.parent_child_utils import ConversationID, set_parent_data


logger = logging.getLogger(__name__)


class MealsEatenViewDataEntry(Enum):
    USER = auto()
    SINGLE_MEAL = auto()
    DATE = auto()
    DATAVIEW_CHAT_ID_MESSAGE_ID = auto()


class MealViewInlineDataKey(InlineButtonDataKey):
    SINGLE_MEAL_SELECTED = auto()
    DAY_VIEW_NAVIGATION = auto()
    SINGLE_MEAL_VIEW_ACTION = auto()


class DayViewNavigationBtnValue(InlineButtonDataValueGroup):
    @staticmethod
    def class_key():
        return MealViewInlineDataKey.DAY_VIEW_NAVIGATION
    NEXT = auto()
    PREVIOUS = auto()
    ENTER_DATE = auto()
    BACK_TO_START_MENU = auto()


class SingleMealActionBtnValue(InlineButtonDataValueGroup):
    @staticmethod
    def class_key():
        return MealViewInlineDataKey.SINGLE_MEAL_VIEW_ACTION
    DELETE_MEAL = auto()
    CONFIRM_DELETE_MEAL = auto()
    BACK_TO_SINGLE_MEAL_VIEW = auto()
    # EDIT_MEAL = auto() TODO
    BACK_TO_DAY_VIEW = auto()


async def message_day_meals(update, context, update_existing):
    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]

    date = dialog_data[MealsEatenViewDataEntry.DATE]

    with get_session() as session:
        meals = select_meals.get_meals_for_one_day(
            session, date,
            dialog_data[MealsEatenViewDataEntry.USER]
        )

    nutrition_total = NutritionType.sum_nutrition_as_dict(meals)
    no_weight_keys = NutritionType.without_weight()
    message = (
        date.strftime("%A %d %B %Y") + "\n"
        "      " + " / ".join([n.value for n in NutritionType if n != NutritionType.WEIGHT]) + "\n" +
        "Total: " + " / ".join([f"{nutrition_total[k]:.0f}" for k in no_weight_keys])
    )

    reply_markup = get_meals_inline_keyboard_markup(meals, context)

    await send_dataview_message(
        update, context, message, reply_markup,
        update_existing
    )


def get_meals_inline_keyboard_markup(meals: list[MealEaten], context):
    buttons = []
    for meal in meals:
        meal_nutrition_dict = meal.nutrition_as_dict()
        message = (
            meal.name + "\n" +
            " / ".join([
                f"{meal_nutrition_dict[k]:.0f}" for k
                in NutritionType.without_weight()
            ])
        )
        buttons.append(
            InlineKeyboardButton(
                message,
                callback_data=MealViewInlineDataKey.SINGLE_MEAL_SELECTED.to_str(
                    value=meal.id
                )
            )
        )

    food_button_rows = [[b] for b in buttons]
    add_meal_button = [
        InlineKeyboardButton(
            "Start menu",
            callback_data=DayViewNavigationBtnValue.BACK_TO_START_MENU.to_key_value_str()
        ),
        InlineKeyboardButton(
            "️Add new meal",
            callback_data=StartConversationDataKey.NEW_MEAL.to_str(
                ConversationID.DAY_VIEW.value
            )
        )
    ]

    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]
    date = dialog_data[MealsEatenViewDataEntry.DATE]
    set_parent_data(context, ConversationID.DAY_VIEW, ConversationID.NEW_MEAL, date)

    navigation_buttons = [
        InlineKeyboardButton(
            "◀", callback_data=DayViewNavigationBtnValue.PREVIOUS.to_key_value_str()
        ),
        InlineKeyboardButton(
            "Date", callback_data=DayViewNavigationBtnValue.ENTER_DATE.to_key_value_str()
        ),
        InlineKeyboardButton(
            "▶", callback_data=DayViewNavigationBtnValue.NEXT.to_key_value_str()
        ),
    ]
    button_rows = food_button_rows + [add_meal_button] + [navigation_buttons]
    return InlineKeyboardMarkup(button_rows)


async def deactivate_dataview_message(context):
    # deletes interactive keyboard
    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]
    if MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID not in dialog_data:
        logger.warning("dataview message data does not exist, message cannot be deactivated")
        return

    chat_id, message_id = dialog_data.pop(MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID)
    await dialog_utils.delete_inline_keyboard(context, chat_id, message_id)


async def delete_dataview_message(context):
    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]
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


async def show_single_meal(update, context, meal: MealEaten):
    message = get_single_meal_message(meal) + "\n"
    reply_markup = single_meal_inline_keyboard_markup(meal.id)
    await send_dataview_message(update, context, message, reply_markup, update_existing=True)


def single_meal_inline_keyboard_markup(meal_id):
    return inline_key_utils.inline_keys_markup(
        ["Delete", "Edit", "Back"],
        [
            SingleMealActionBtnValue.DELETE_MEAL.to_key_value_str(),
            StartConversationDataKey.EDIT_MEAL.to_str(meal_id),
            SingleMealActionBtnValue.BACK_TO_DAY_VIEW.to_key_value_str()
        ]
    )


async def ask_for_delete_confirmation(update, context, meal: MealEaten):
    meal_description = get_single_meal_message(meal)
    question = "Confirm meal entry deletion?"
    message = meal_description + "\n\n" + question
    await send_dataview_message(
        update, context, message,
        delete_confirmation_markup(), update_existing=True
    )


def get_single_meal_message(meal):
    return meal.describe()


def delete_confirmation_markup():
    return inline_key_utils.inline_keys_markup(
        ["Confirm", "Go back"],
        [
            SingleMealActionBtnValue.CONFIRM_DELETE_MEAL.to_key_value_str(),
            SingleMealActionBtnValue.BACK_TO_SINGLE_MEAL_VIEW.to_key_value_str()
        ]
    )


async def send_dataview_message(update, context, text, reply_markup, update_existing):
    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]

    if update_existing and MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID in dialog_data:
        chat_id, message_id = dialog_data[MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID]

        await dialog_utils.edit_message(
            context, chat_id=chat_id, message_id=message_id,
            text=text, reply_markup=reply_markup,
        )
    else:
        message_obj = await update.effective_message.reply_text(
            text, reply_markup=reply_markup
        )
        dialog_data[MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID] = (
            message_obj.chat.id, message_obj.id
        )
