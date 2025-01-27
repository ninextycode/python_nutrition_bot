from telegram.ext import ConversationHandler, CommandHandler
from chatbot.config import Commands
from enum import Enum, auto
from chatbot import dialog_utils
from chatbot.parent_child_utils import ChildEndStage
from database import common_sql
from database.select import select_users
from chatbot.start_menu import start_menu_utils


class StartStages(Enum):
    # CHOOSE_ACTION = auto()
    EXISTING_USER_CHOOSE_ACTION = auto()
    NEW_USER_CHOOSE_ACTION = auto()


def get_start_menu_conversation_handler(
    new_user_command_handlers,
    existing_user_command_handlers,
):
    entry_points = [
        CommandHandler(Commands.START.value, create_start_options)
    ]

    states = {
        StartStages.NEW_USER_CHOOSE_ACTION: \
            new_user_command_handlers,
        StartStages.EXISTING_USER_CHOOSE_ACTION: \
            existing_user_command_handlers,
        ChildEndStage.NEW_MEAL_END: \
            existing_user_command_handlers,
        ChildEndStage.MEALS_EATEN_VIEW_END: \
            existing_user_command_handlers,
        ChildEndStage.RETURN_TO_START: \
            existing_user_command_handlers
    }

    for k in states.keys():
        states[k].extend(entry_points)

    fallbacks = [
        CommandHandler(Commands.CANCEL.value, handle_cancel)
    ]
    handler = ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=fallbacks,
    )
    return handler


async def create_start_options(update, callback):
    user = dialog_utils.get_tg_user_obj(update)
    if user is None:
        await start_menu_utils.send_new_user_options(update)
        return StartStages.NEW_USER_CHOOSE_ACTION
    else:
        await start_menu_utils.send_existing_user_options(
            update, user
        )
        return StartStages.EXISTING_USER_CHOOSE_ACTION


async def handle_cancel(update, context):
    await dialog_utils.no_markup_message(
        update,
        (
            "Interaction stopped.\n" +
            f"Use /{Commands.START.value} to start again"
        )
    )
    return ConversationHandler.END
