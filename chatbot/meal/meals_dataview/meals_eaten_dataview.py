import datetime
from telegram.ext import filters
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler
from enum import Enum, auto
from chatbot.config import Commands
from chatbot.inline_key_utils import InlineButtonDataKeyValue, StartConversationDataKey
from database.update import update_meals
from chatbot import dialog_utils
from database.common_sql import get_session
from database.select import select_meals
from chatbot.meal.meals_dataview import meals_dataview_utils
from chatbot.meal.meals_dataview.meals_dataview_utils import (
    MealsEatenViewDataEntry, MealViewInlineDataKey,
    DayViewNavigationBtnValue, SingleMealActionBtnValue
)
from chatbot.start_menu import start_menu_utils
from chatbot.parent_child_utils import ChildEndStage
from chatbot.config import DataKeys
import dateparser
import logging
import traceback


logger = logging.getLogger(__name__)


class MealsEatenViewStages(Enum):
    DAY_VIEW = auto()
    DATE_ENTRY = auto()
    SINGLE_MEAL_VIEW = auto()


def get_meals_eaten_view_conversation_handler(new_meal_conversation_handler):
    text_only_filter = filters.TEXT & ~filters.COMMAND
    entry_points = [
        CommandHandler(
            Commands.VIEW_MEALS_EATEN.value, open_meals_eaten_view
        ),
        CallbackQueryHandler(
            handle_inline_key_start_callback,
            pattern=StartConversationDataKey.VIEW_EATEN_MEALS.value
        )
    ]

    day_view_handlers = [
        CallbackQueryHandler(
            handle_date_view_navigation_callback,
            pattern=MealViewInlineDataKey.DAY_VIEW_NAVIGATION.value
        ),
        CallbackQueryHandler(
            handle_open_single_meal_callback,
            pattern=MealViewInlineDataKey.SINGLE_MEAL_SELECTED.value
        ),
        new_meal_conversation_handler
    ]
    states = {
        MealsEatenViewStages.DAY_VIEW: day_view_handlers,
        ChildEndStage.NEW_MEAL_END: day_view_handlers,
        MealsEatenViewStages.DATE_ENTRY: [MessageHandler(text_only_filter, handle_date)],
        MealsEatenViewStages.SINGLE_MEAL_VIEW: [
            CallbackQueryHandler(
                handle_single_meal_callback,
                pattern=MealViewInlineDataKey.SINGLE_MEAL_VIEW_ACTION.value
            )
        ]
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
        map_to_parent={
            ConversationHandler.END: ChildEndStage.MEALS_EATEN_VIEW_END
        }
    )
    return handler


async def handle_inline_key_start_callback(update, context):
    await dialog_utils.handle_inline_keyboard_callback(
        update
    )
    return await open_meals_eaten_view(update, context)


async def open_meals_eaten_view(update, context):
    # cleanup old dialog window if it exists
    old_dialog_data = context.user_data.get(DataKeys.MEALS_EATEN_DATAVIEW, dict())
    if MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID in old_dialog_data:
        await meals_dataview_utils.deactivate_dataview_message(context)

    context.user_data[DataKeys.MEALS_EATEN_DATAVIEW] = dict()
    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]

    user = dialog_utils.get_tg_user_obj(update)

    if user is None:
        await dialog_utils.user_does_not_exist_message(update)
        return ConversationHandler.END

    dialog_data[MealsEatenViewDataEntry.USER] = user
    dialog_data[MealsEatenViewDataEntry.DATE] = user.get_datetime_now().date()

    await meals_dataview_utils.message_day_meals(
        update, context, update_existing=False
    )
    return MealsEatenViewStages.DAY_VIEW


async def handle_date_view_navigation_callback(update, context):
    await dialog_utils.handle_inline_keyboard_callback(
        update
    )
    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]

    data_str = update.callback_query.data
    data = InlineButtonDataKeyValue.from_str(data_str)

    if data.value == DayViewNavigationBtnValue.PREVIOUS.value:
        dialog_data[MealsEatenViewDataEntry.DATE] -= datetime.timedelta(days=1)
        await meals_dataview_utils.message_day_meals(
            update, context, update_existing=True
        )
        return MealsEatenViewStages.DAY_VIEW
    elif data.value == DayViewNavigationBtnValue.NEXT.value:
        dialog_data[MealsEatenViewDataEntry.DATE] += datetime.timedelta(days=1)
        await meals_dataview_utils.message_day_meals(
            update, context, update_existing=True
        )
        return MealsEatenViewStages.DAY_VIEW
    elif data.value == DayViewNavigationBtnValue.ENTER_DATE.value:
        await meals_dataview_utils.deactivate_dataview_message(context)
        await meals_dataview_utils.ask_for_date(update)
        return MealsEatenViewStages.DATE_ENTRY
    elif data.value == DayViewNavigationBtnValue.BACK_TO_START_MENU.value:
        user = dialog_data[MealsEatenViewDataEntry.USER]
        await meals_dataview_utils.deactivate_dataview_message(context)
        await start_menu_utils.send_existing_user_options(
            update, user
        )
        return ConversationHandler.END

    # if callback was not handled by this point, there is an error
    error_message = "handle_date_view_callback Unexpected data received: " + data_str
    return await handle_exception_back_to_day_view(update, context, error_message)


async def handle_open_single_meal_callback(update, context):
    await dialog_utils.handle_inline_keyboard_callback(
        update
    )
    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]
    data_str = update.callback_query.data
    data = InlineButtonDataKeyValue.from_str(data_str)
    meal_id = data.value
    try:
        with get_session() as session:
            meal = select_meals.select_meal_eaten_by_meal_id(session, meal_id)
        if meal is None:
            error_message = f"Meal with id {meal_id} does not exist"
            logger.error(error_message)
            raise ValueError(error_message)
    except Exception as e:
        return await handle_exception_back_to_day_view(update, context, e)

    await meals_dataview_utils.show_single_meal(
        update, context, meal
    )
    dialog_data[MealsEatenViewDataEntry.SINGLE_MEAL] = meal
    return MealsEatenViewStages.SINGLE_MEAL_VIEW



async def handle_date(update, context):
    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]
    # dateparser can handle today / yesterday word
    date_str = update.message.text
    timezone_str = dialog_data[MealsEatenViewDataEntry.USER].timezone_obj.timezone
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
    await dialog_utils.handle_inline_keyboard_callback(
        update
    )

    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]

    data_str = update.callback_query.data
    data = InlineButtonDataKeyValue.from_str(data_str)

    meal = dialog_data[MealsEatenViewDataEntry.SINGLE_MEAL]

    if data.value == SingleMealActionBtnValue.DELETE_MEAL.value:
        await meals_dataview_utils.ask_for_delete_confirmation(
            update, context, meal
        )
        return MealsEatenViewStages.SINGLE_MEAL_VIEW

    elif data.value == SingleMealActionBtnValue.BACK_TO_SINGLE_MEAL_VIEW.value:
        await meals_dataview_utils.show_single_meal(
            update, context, meal
        )
        return MealsEatenViewStages.SINGLE_MEAL_VIEW

    elif data.value == SingleMealActionBtnValue.CONFIRM_DELETE_MEAL.value:
        dialog_data.pop(MealsEatenViewDataEntry.SINGLE_MEAL)

        try:
            with get_session() as session:
                update_meals.delete_meal_eaten(session, meal)
        except Exception as e:
            return await handle_exception_back_to_day_view(update, context, e)

        await meals_dataview_utils.message_day_meals(
            update, context, update_existing=True
        )
        return MealsEatenViewStages.DAY_VIEW

    elif data.value == SingleMealActionBtnValue.BACK_TO_DAY_VIEW.value:
        dialog_data.pop(MealsEatenViewDataEntry.SINGLE_MEAL)
        await meals_dataview_utils.message_day_meals(
            update, context, update_existing=True
        )
        return MealsEatenViewStages.DAY_VIEW

    # if callback was not handled by this point, there is an error
    error_message = "handle_single_meal_callback Unexpected data received: " + data_str
    return await handle_exception_back_to_day_view(update, context, error_message)


async def handle_exception_back_to_day_view(update, context, e):
    logger.error(f"{e}" + "\n" + f"{traceback.format_exc()}")
    error_message = str(e)
    logger.error(error_message)
    await meals_dataview_utils.delete_dataview_message(context)
    await dialog_utils.no_markup_message(update, error_message)
    await meals_dataview_utils.message_day_meals(
        update, context, update_existing=True
    )
    return MealsEatenViewStages.DAY_VIEW


async def handle_cancel(update, context):
    dialog_data = context.user_data[DataKeys.MEALS_EATEN_DATAVIEW]
    if MealsEatenViewDataEntry.DATAVIEW_CHAT_ID_MESSAGE_ID in dialog_data:
        await meals_dataview_utils.deactivate_dataview_message(context)

    message = "Meals view dialog ended"

    command = update.message.text
    is_cancel_command = command.lower() in ["/cancel", "cancel"]
    if is_cancel_command:
        await dialog_utils.no_markup_message(update, message)
    else:
        await dialog_utils.keep_markup_message(
            update, message
        )

    return ConversationHandler.END
