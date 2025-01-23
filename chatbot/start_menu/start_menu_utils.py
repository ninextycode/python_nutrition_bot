from chatbot.inline_key_utils import StartConversationDataKey
from chatbot import inline_key_utils
from chatbot.parent_child_utils import ConversationID


async def send_new_user_options(update):
    reply_markup = inline_key_utils.inline_keys_markup(
        ["Register new user"],
        [StartConversationDataKey.NEW_USER.to_str(ConversationID.START_MENU.value)]
    )
    await update.effective_message.reply_text(
        f"Hello {update.message.from_user}!\n"
        "Your user account does not exist. You need to register.",
        reply_markup=reply_markup
    )


async def send_existing_user_options(update, user):
    reply_markup = inline_key_utils.inline_keys_markup(
        [
            "Update user data",
            "Create new meal",
            "View eaten meals",
            "View saved meals",
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
        f"Hi {user.name}!\n"
        "Please select an action", reply_markup=reply_markup
    )
