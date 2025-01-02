import datetime
from telegram import ReplyKeyboardRemove
from telegram.ext import filters
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler
from enum import Enum, auto
from chatbot.config import Commands
from database import common_sql
from database.select import select_users
from database.update import update_meals
from chatbot import dialog_utils
from database.common_sql import get_session
from chatbot.meal.meals_dataview import meals_dataview_utils
from chatbot.meal.meals_dataview.meals_dataview_utils import (
    MealsEatenViewDataEntry, InlineKeyDataPayload, InlineKeyData, DateNavigationOption,
    MEALS_EATEN_DB
)
import pytz
import dateparser
import logging
import traceback


logger = logging.getLogger(__name__)


class MealsEatenViewStages(Enum):
    DAY_VIEW = auto()
    DATE_ENTRY = auto()
    SINGLE_MEAL_VIEW = auto()


def get_meals_eaten_view_conversation_handler():
    text_only_filter = filters.TEXT & ~filters.COMMAND
    entry_points = [
        CommandHandler(Commands.VIEW_MEALS_EATEN, open_meals_eaten_view)
    ]
    states = {
        MealsEatenViewStages.DAY_VIEW: [CallbackQueryHandler(handle_date_view_callback)],
        MealsEatenViewStages.DATE_ENTRY: [MessageHandler(text_only_filter, handle_date)],
        MealsEatenViewStages.SINGLE_MEAL_VIEW: [CallbackQueryHandler(handle_single_meal_callback)]
    }
    # allows to restart dialog from the middle
    for k in states.keys():
        states[k].extend(entry_points)

    fallbacks = [
        CommandHandler("cancel", handle_cancel),
        MessageHandler(filters.COMMAND, handle_cancel)
    ]
    handler = ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=fallbacks,
    )
    return handler


async def open_meals_eaten_view(update, context):
    if MEALS_EATEN_DB in context.user_data:
        await meals_dataview_utils.delete_dataview_message(context)

    context.user_data[MEALS_EATEN_DB] = dict()
    dialog_data = context.user_data[MEALS_EATEN_DB]

    tg_id = update.message.from_user.id

    with common_sql.get_session() as session:
        user = select_users.select_user_by_telegram_id(
            session, tg_id
        )

    if user is None:
        response = "User does not exists. "
        response += f"Use /{Commands.NEW_USER} instead"
        await update.message.reply_text(
            response, reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    else:
        dialog_data[MealsEatenViewDataEntry.USER_ID] = user.id
        dialog_data[MealsEatenViewDataEntry.USER_TIMEZONE] = pytz.timezone(
            user.timezone_obj.timezone
        )

    dialog_data[MealsEatenViewDataEntry.DATE] = datetime.datetime.now(
        tz=dialog_data[MealsEatenViewDataEntry.USER_TIMEZONE]
    )

    await meals_dataview_utils.message_day_meals(
        update, context, update_existing=False
    )
    return MealsEatenViewStages.DAY_VIEW


async def handle_date_view_callback(update, context):
    await update.callback_query.answer()
    dialog_data = context.user_data[MEALS_EATEN_DB]

    data_str = update.callback_query.data
    data = InlineKeyDataPayload.from_str(data_str)

    if data.key == InlineKeyData.DATE_NAVIGATION.value:
        if data.value == DateNavigationOption.PREVIOUS.value:
            dialog_data[MealsEatenViewDataEntry.DATE] -= datetime.timedelta(days=1)
            await meals_dataview_utils.message_day_meals(
                update, context, update_existing=True
            )
            return MealsEatenViewStages.DAY_VIEW
        elif data.value == DateNavigationOption.NEXT.value:
            dialog_data[MealsEatenViewDataEntry.DATE] += datetime.timedelta(days=1)
            await meals_dataview_utils.message_day_meals(
                update, context, update_existing=True
            )
            return MealsEatenViewStages.DAY_VIEW
        elif data.value == DateNavigationOption.ENTER_DATE.value:
            await meals_dataview_utils.delete_dataview_message(context)
            await meals_dataview_utils.ask_for_date(update)
            return MealsEatenViewStages.DATE_ENTRY

    elif data.key == InlineKeyData.SINGLE_MEAL_SELECTION.value:
        meal_id = data.value
        try:
            await meals_dataview_utils.message_single_meal(
                update, context, meal_id, update_existing=True
            )
        except Exception as e:
            return await handle_exception_back_to_day_view(update, context, e)

        dialog_data[MealsEatenViewDataEntry.SINGLE_MEAL_ID] = meal_id
        return MealsEatenViewStages.SINGLE_MEAL_VIEW

    # if callback was not handled by this point, there is an error
    error_message = "handle_date_view_callback Unexpected data received: " + data_str
    logger.error(error_message)
    await dialog_utils.no_markup_message(update, error_message)


async def give_individual_meal_view(update, context):
    return await handle_cancel(update, context)  # TODO


async def handle_date(update, context):
    dialog_data = context.user_data[MEALS_EATEN_DB]
    # dateparser can handle today / yesterday word
    date_str = update.message.text
    timezone_str = str(dialog_data[MealsEatenViewDataEntry.USER_TIMEZONE])
    datetime_obj = dateparser.parse(
        date_str,
        settings={
            "DATE_ORDER": "DMY",
            "TIMEZONE": timezone_str
        }
    )

    if datetime_obj is None:
        await dialog_utils.wrong_value_message(update)
        await meals_dataview_utils.ask_for_date(update)
        return MealsEatenViewStages.DATE_ENTRY

    date = datetime_obj.date()
    dialog_data[MealsEatenViewDataEntry.DATE] = date
    await meals_dataview_utils.message_day_meals(
        update, context, update_existing=False
    )
    return MealsEatenViewStages.DAY_VIEW


async def handle_single_meal_callback(update, context):
    await update.callback_query.answer()
    dialog_data = context.user_data[MEALS_EATEN_DB]

    data_str = update.callback_query.data
    data = InlineKeyDataPayload.from_str(data_str)

    if data.key == InlineKeyData.DELETE_MEAL.value:
        meal_id = dialog_data.pop(MealsEatenViewDataEntry.SINGLE_MEAL_ID)
        try:
            with get_session() as session:
                update_meals.delete_meal_eaten(session, meal_id)
        except Exception as e:
            return await handle_exception_back_to_day_view(update, context, e)

        await meals_dataview_utils.message_day_meals(
            update, context, update_existing=True
        )
        return MealsEatenViewStages.DAY_VIEW

    elif data.key == InlineKeyData.BACK_TO_DAY_VIEW.value:
        await meals_dataview_utils.message_day_meals(
            update, context, update_existing=True
        )
        return MealsEatenViewStages.DAY_VIEW

    # if callback was not handled by this point, there is an error
    error_message = "handle_single_meal_callback Unexpected data received: " + data_str
    logger.error(error_message)
    await dialog_utils.no_markup_message(update, error_message)


async def handle_exception_back_to_day_view(update, context, e):
    logger.error(f"{e}" + "\n" + f"{traceback.format_exc()}")
    error_message = str(e)
    logger.error(error_message)
    await dialog_utils.no_markup_message(update, error_message)
    await meals_dataview_utils.message_day_meals(
        update, context, update_existing=True
    )
    return MealsEatenViewStages.DAY_VIEW


async def handle_cancel(update, context):
    await meals_dataview_utils.delete_dataview_message(context)
    await dialog_utils.keep_markup_message(update, "Meals view dialog ended")
    return ConversationHandler.END
