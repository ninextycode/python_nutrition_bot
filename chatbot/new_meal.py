from telegram.ext import filters
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler
from chatbot.config import Commands, u_reg
from enum import Enum, auto
from chatbot import dialog_utils
from chatbot import new_meal_utils
from chatbot.new_meal_utils import InputMode, UserDataFields
from database import update_mysql, common_mysql, select_mysql
from pathlib import Path


import tempfile


class NewMealStages(Enum):
    CHOOSE_INPUT_MODE = auto()
    ADD_DATA_FOR_AI = auto()
    CONFIRM_AI_RESPONSE = auto()
    DESCRIBE_MEAL_MANUALLY = auto()
    CONFIRM_NAME_ESTIMATE = auto()
    ADJUST_ESTIMATE = auto()
    INPUT_NUTRITION = auto()
    CONFIRM_DATA = auto()


MEAL_DATA = "MEAL_DATA"


async def process_new_meal(update, context):
    pass


def get_new_meal_conversation_handler():
    text_only_filter = filters.TEXT & ~filters.COMMAND
    entry_points = [
        CommandHandler(Commands.NEW_MEAL, on_new_meal),
    ]
    states = {
        NewMealStages.CHOOSE_INPUT_MODE: [MessageHandler(text_only_filter, on_choose_input_mode)],
        NewMealStages.INPUT_NUTRITION: [MessageHandler(text_only_filter, on_enter_nutrition_manually)],
        NewMealStages.ADD_DATA_FOR_AI: [
            MessageHandler(text_only_filter, on_describe_for_ai),
            MessageHandler(filters.PHOTO, on_image_for_ai),
            CallbackQueryHandler(callback=skip_description_button_callback)
        ],
        NewMealStages.CONFIRM_AI_RESPONSE: []
    }
    # allows to restart dialog from the middle
    for k in states.keys():
        states[k].extend(entry_points)
    fallbacks = [
        CommandHandler("cancel", on_cancel),
        MessageHandler(filters.COMMAND, on_cancel)
    ]
    handler = ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=fallbacks,
    )
    return handler


async def on_new_meal(update, context):
    if MEAL_DATA in context.user_data:
        await new_meal_utils.remove_last_skip_button(context, context.user_data[MEAL_DATA])

    context.user_data[MEAL_DATA] = dict()
    meal_data = context.user_data[MEAL_DATA]

    tg_id = update.message.from_user.id

    with common_mysql.get_connection() as connection:
        existing_user_data = select_mysql.select_user_by_telegram_id(
            connection, tg_id
        )

    if existing_user_data is None:
        return dialog_utils.user_does_not_exist_message(update)

    meal_data[UserDataFields.NAME] = existing_user_data["Name"]

    await update.message.reply_text(
        f"Hi {meal_data[UserDataFields.NAME]}! Let's add a new meal. \n",
        reply_markup=ReplyKeyboardRemove()
    )
    await new_meal_utils.input_mode_question(update)
    return NewMealStages.CHOOSE_INPUT_MODE


async def on_choose_input_mode(update, context):
    meal_data = context.user_data[MEAL_DATA]

    input_mode = update.message.text
    if input_mode not in InputMode:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.input_mode_question(update)
        return NewMealStages.CHOOSE_INPUT_MODE

    meal_data[UserDataFields.IS_USING_AI] = (input_mode == InputMode.AI)

    if input_mode == InputMode.AI.value:
        await new_meal_utils.ai_input_question(update)
        return NewMealStages.ADD_DATA_FOR_AI

    elif input_mode == InputMode.MANUAL.value:
        await update.message.reply_text(
            (
                "Specify nutrition manually."
                "Use the following format:\n"
                "<name>\n"
                "protein X (g)\n"
                "fat (g) X\n"
                "carb X (g)\n"
                "calories X (kcal)"
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        return NewMealStages.INPUT_NUTRITION

    elif input_mode == InputMode.BARCODE.value:
        await dialog_utils.wrong_value_message(update, "not implemented")
        await new_meal_utils.input_mode_question(update)
        return NewMealStages.CHOOSE_INPUT_MODE
    else:
        await dialog_utils.wrong_value_message(update, "Unexpected value")
        await new_meal_utils.input_mode_question(update)
        return NewMealStages.CHOOSE_INPUT_MODE


async def on_describe_for_ai(update, context):
    print("update.callback_query", update.callback_query)
    meal_data = context.user_data[MEAL_DATA]
    await new_meal_utils.remove_last_skip_button(context, meal_data)

    description = update.message.text
    print("on_describe_for_ai", description)
    description = description.strip()
    meal_data[UserDataFields.DESCRIPTION_FOR_AI] = description
    if UserDataFields.IMAGE_FILE not in meal_data:
        await new_meal_utils.ask_for_picture(update, meal_data)
        return NewMealStages.ADD_DATA_FOR_AI
    else:
        await process_ai_request(update, context)
        return NewMealStages.CONFIRM_AI_RESPONSE


async def on_image_for_ai(update, context):
    print("update.callback_query", update.callback_query)
    meal_data = context.user_data[MEAL_DATA]
    await new_meal_utils.remove_last_skip_button(context, meal_data)

    caption = update.message.caption

    images_different_res = update.message.photo

    print("on_image_for_ai", caption, len(images_different_res))

    if len(images_different_res) == 0:
        await dialog_utils.no_markup_message(update, "Failed to get an image.")
        await new_meal_utils.ask_for_picture(update, meal_data)
        return NewMealStages.ADD_DATA_FOR_AI

    image_highest_res = images_different_res[-1]

    image_info = await image_highest_res.get_file()

    directory = Path("./images")
    directory.mkdir(parents=True, exist_ok=True)

    print("file_path", image_info.file_path)
    extension = Path(image_info.file_path).suffix
    temp_f = tempfile.TemporaryFile()
    await image_info.download_to_memory(temp_f)
    temp_f.seek(0)

    count = sum([obj.is_file() for obj in directory.iterdir()])

    local_file_path = directory / f"./image_{count}{extension}"
    print("writing to", local_file_path)
    open(local_file_path, "wb").write(temp_f.read())

    meal_data[UserDataFields.IMAGE_FILE] = str(local_file_path)

    # use caption as description if description data was not specified
    # or was explicitly skipped (is None check)
    if caption is not None and (
           UserDataFields.DESCRIPTION_FOR_AI not in meal_data or
           meal_data[UserDataFields.DESCRIPTION_FOR_AI] is None
    ):
        meal_data[UserDataFields.DESCRIPTION_FOR_AI] = caption

    if UserDataFields.DESCRIPTION_FOR_AI not in meal_data:
        await new_meal_utils.ask_for_description(update, meal_data)
        return NewMealStages.ADD_DATA_FOR_AI
    else:
        await process_ai_request(update, context)
        return NewMealStages.CONFIRM_AI_RESPONSE


async def skip_description_button_callback(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_reply_markup(None)

    meal_data = context.user_data[MEAL_DATA]
    print("update.callback_query", update.callback_query)
    print("update.callback_query.inline_message_id", update.callback_query.inline_message_id)

    enum_obj = UserDataFields(update.callback_query.data)
    meal_data[enum_obj] = None

    if enum_obj == UserDataFields.DESCRIPTION_FOR_AI:
        await dialog_utils.no_markup_message(update, "Text description skipped")
    elif enum_obj == UserDataFields.IMAGE_FILE:
        await dialog_utils.no_markup_message(update, "Image skipped")
    else:
        await dialog_utils.no_markup_message(update, "Unexpected data key skipped: " + repr(enum_obj))

    if UserDataFields.DESCRIPTION_FOR_AI not in meal_data:
        await new_meal_utils.ask_for_description(update, meal_data)
        return NewMealStages.ADD_DATA_FOR_AI
    elif UserDataFields.IMAGE_FILE not in meal_data:
        await new_meal_utils.ask_for_picture(update, meal_data)
        return NewMealStages.ADD_DATA_FOR_AI
    else:
        await process_ai_request(update, context)
        return NewMealStages.CONFIRM_AI_RESPONSE


async def process_ai_request(update, context):
    await dialog_utils.no_markup_message(update, "got data for ai")
    meal_data = context.user_data[MEAL_DATA]
    description = meal_data.get(UserDataFields.DESCRIPTION_FOR_AI, None)
    image = meal_data.get(UserDataFields.IMAGE_FILE, None)
    await dialog_utils.no_markup_message(update, "Description: " + str(description))
    await dialog_utils.no_markup_message(update, "Image: " + str(image))

    print("description", description)
    print("image", image)


async def on_new_meal_mode_selected(update, context):
    pass


async def on_enter_nutrition_manually(update, context):
    nutrition_data = new_meal_utils.parse_meal_message(update.message.text)
    keys = ["name"] + new_meal_utils.nutrition_tags
    message_lines = []
    for k in keys:
        l = f"{k} - {nutrition_data[k]}"
        print(l)
        message_lines.append(l)

    await update.message.reply_text(
        "\n".join(message_lines), reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def on_wrong_format(update, context):
    pass


async def on_use_ai(update, context):
    pass


async def on_describe_meal(update, context):
    pass


async def on_nutrition_confirmed(update, context):
    pass


async def on_name_given(update, context):
    pass


async def on_meal_confirmed(update, context):
    pass


async def on_confirm_estimate(update, context):
    pass


async def on_cancel(update, context):
    await update.message.reply_text(
        "New meal entry cancelled",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END



