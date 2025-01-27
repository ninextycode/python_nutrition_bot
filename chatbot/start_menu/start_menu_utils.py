from chatbot.inline_key_utils import StartConversationDataKey
from chatbot import inline_key_utils, dialog_utils
from chatbot.parent_child_utils import ConversationID, ChildEndStage


async def send_new_user_options(update):
    await dialog_utils.no_markup_message(
        update, f"Hello {update.message.from_user}!"
    )
    reply_markup = inline_key_utils.inline_keys_markup(
        ["Register new user"],
        [StartConversationDataKey.NEW_USER.to_str(ConversationID.START_MENU.value)]
    )
    await update.effective_message.reply_text(
        "Your user account does not exist. You need to register.",
        reply_markup=reply_markup
    )


async def send_existing_user_options(update, user):
    await dialog_utils.no_markup_message(
        update, f"Hi {user.name}!"
    )

    reply_markup = inline_key_utils.inline_keys_markup(
        [
            "Update user data",
            "Create new meal",
            "View meals",
            "View archived meals",
            "Check nutrition target"
        ],
        [
            StartConversationDataKey.UPDATE_USER.to_str(ConversationID.START_MENU.value),
            StartConversationDataKey.NEW_MEAL.to_str(ConversationID.START_MENU.value),
            StartConversationDataKey.VIEW_EATEN_MEALS.to_str(ConversationID.START_MENU.value),
            StartConversationDataKey.VIEW_SAVED_MEALS.to_str(ConversationID.START_MENU.value),
            StartConversationDataKey.NUTRITION.to_str(ConversationID.START_MENU.value)
        ],
        1
    )
    await update.effective_message.reply_text(
        "Please select an action", reply_markup=reply_markup
    )


async def handle_return_to_start(update, context):
    # common handler for child conversation to return to start menu
    user = dialog_utils.get_tg_user_obj(update)
    await send_existing_user_options(update, user)
    return ChildEndStage.RETURN_TO_START
