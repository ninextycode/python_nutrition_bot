from telegram.ext import filters
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler
from chatbot.config import Commands, u_reg
from enum import Enum, auto
from chatbot import dialog_utils
from chatbot import new_meal_utils
from chatbot.new_meal_utils import (
    MEAL_DATA, UserDataEntry,
    InputMode, ConfirmAiOption, ConfirmManualOption, KeepUpdateOption
)
from database import update_mysql, common_mysql, select_mysql
from pathlib import Path


import tempfile


class NewMealStages(Enum):
    CHOOSE_INPUT_MODE = auto()

    ADD_DATA_FOR_AI = auto()
    ADD_IMAGE_FOR_AI = auto()
    ADD_DESCRIPTION_FOR_AI = auto()
    CONFIRM_AI_ESTIMATE = auto()

    DESCRIBE_MEAL_MANUALLY = auto()
    ADD_NUTRITION_VALUES_MANUALLY = auto()
    CONFIRM_MANUAL_DATA = auto()

    CONFIRM_EXISTING_NAME_DESCRIPTION = auto()
    CONFIRM_EXISTING_NUTRITION = auto()


def get_new_meal_conversation_handler():
    text_only_filter = filters.TEXT & ~filters.COMMAND
    entry_points = [
        CommandHandler(Commands.NEW_MEAL, handle_new_meal),
    ]
    states = {
        NewMealStages.CHOOSE_INPUT_MODE: [
            MessageHandler(text_only_filter, handle_choose_input_mode)
        ],
        NewMealStages.ADD_DATA_FOR_AI: [
            MessageHandler(text_only_filter, handle_describe_for_ai),
            MessageHandler(filters.PHOTO, handle_image_for_ai),
        ],
        NewMealStages.ADD_IMAGE_FOR_AI: [
            MessageHandler(filters.PHOTO, handle_image_for_ai),
            CallbackQueryHandler(callback=skip_description_button_callback)
        ],
        NewMealStages.ADD_DESCRIPTION_FOR_AI: [
            MessageHandler(text_only_filter, handle_describe_for_ai),
            CallbackQueryHandler(callback=skip_description_button_callback)
        ],
        NewMealStages.CONFIRM_AI_ESTIMATE: [
            MessageHandler(text_only_filter, handle_confirm_ai_estimate)
        ],
        NewMealStages.DESCRIBE_MEAL_MANUALLY: [
            MessageHandler(text_only_filter, handle_describe_manually)
        ],
        NewMealStages.ADD_NUTRITION_VALUES_MANUALLY: [
            MessageHandler(text_only_filter, handle_add_nutrition_manually)
        ],
        NewMealStages.CONFIRM_MANUAL_DATA: [
            MessageHandler(text_only_filter, handle_confirm_manual_entry_data)
        ],
        NewMealStages.CONFIRM_EXISTING_NAME_DESCRIPTION: [
            MessageHandler(text_only_filter, handle_confirm_existing_description)
        ],
        NewMealStages.CONFIRM_EXISTING_NUTRITION: [
            MessageHandler(text_only_filter, handle_confirm_existing_nutrition)
        ]
    }
    # allows to restart dialog from the middle
    for k in states.keys():
        states[k].extend(entry_points)
    fallbacks = [
        CommandHandler("cancel", handle_cancel),
        # this would cancel the dialog if any new command is called
        MessageHandler(filters.COMMAND, handle_cancel)
    ]
    handler = ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=fallbacks,
    )
    return handler


async def handle_new_meal(update, context):
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

    meal_data[UserDataEntry.USER_NAME] = existing_user_data["Name"]

    await update.message.reply_text(
        f"Hi {meal_data[UserDataEntry.USER_NAME]}! Let's add a new meal. \n",
        reply_markup=ReplyKeyboardRemove()
    )
    await new_meal_utils.input_mode_question(update)
    return NewMealStages.CHOOSE_INPUT_MODE


async def handle_choose_input_mode(update, context):
    meal_data = context.user_data[MEAL_DATA]

    input_mode = update.message.text
    if input_mode not in InputMode:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.input_mode_question(update)
        return NewMealStages.CHOOSE_INPUT_MODE

    meal_data[UserDataEntry.IS_USING_AI] = (input_mode == InputMode.AI)

    if input_mode == InputMode.AI.value:
        await new_meal_utils.ai_input_question(update)
        return NewMealStages.ADD_DATA_FOR_AI

    elif input_mode == InputMode.MANUAL.value:
        await new_meal_utils.ask_for_meal_description(update)
        return NewMealStages.DESCRIBE_MEAL_MANUALLY

    elif input_mode == InputMode.BARCODE.value:
        await dialog_utils.wrong_value_message(update, "not implemented")
        await new_meal_utils.input_mode_question(update)
        return NewMealStages.CHOOSE_INPUT_MODE
    else:
        await dialog_utils.wrong_value_message(update, "Unexpected value")
        await new_meal_utils.input_mode_question(update)
        return NewMealStages.CHOOSE_INPUT_MODE


async def handle_describe_for_ai(update, context):
    print("update.callback_query", update.callback_query)
    meal_data = context.user_data[MEAL_DATA]
    await new_meal_utils.remove_last_skip_button(context, meal_data)

    description = update.message.text
    print("on_describe_for_ai", description)
    description = description.strip()
    meal_data[UserDataEntry.DESCRIPTION_FOR_AI] = description
    if UserDataEntry.IMAGE_FILE not in meal_data:
        await new_meal_utils.ask_for_picture(update, meal_data)
        return NewMealStages.ADD_IMAGE_FOR_AI
    else:
        await process_ai_request(update, context)
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def handle_image_for_ai(update, context):
    print("update.callback_query", update.callback_query)
    meal_data = context.user_data[MEAL_DATA]
    await new_meal_utils.remove_last_skip_button(context, meal_data)

    caption = update.message.caption

    images_different_res = update.message.photo

    print("on_image_for_ai", caption, len(images_different_res))

    if len(images_different_res) == 0:
        await dialog_utils.no_markup_message(update, "Failed to get an image.")
        await new_meal_utils.ask_for_picture(update, meal_data)
        return NewMealStages.ADD_IMAGE_FOR_AI

    for i, im_obj in enumerate(images_different_res):
        print(
            "image", i,
            "has size", im_obj.height, "x", im_obj.width,
            "and size", im_obj.file_size, "bytes"
        )

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

    meal_data[UserDataEntry.IMAGE_FILE] = str(local_file_path)

    # use caption as description if description data was not specified
    # or was explicitly skipped (is None check)
    if caption is not None and (
            UserDataEntry.DESCRIPTION_FOR_AI not in meal_data or
            meal_data[UserDataEntry.DESCRIPTION_FOR_AI] is None
    ):
        meal_data[UserDataEntry.DESCRIPTION_FOR_AI] = caption

    if UserDataEntry.DESCRIPTION_FOR_AI not in meal_data:
        await new_meal_utils.ask_for_description(update, meal_data)
        return NewMealStages.ADD_DESCRIPTION_FOR_AI
    else:
        await process_ai_request(update, context)
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def skip_description_button_callback(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_reply_markup(None)

    meal_data = context.user_data[MEAL_DATA]
    print("update.callback_query", update.callback_query)
    print("update.callback_query.inline_message_id", update.callback_query.inline_message_id)

    enum_obj = UserDataEntry(update.callback_query.data)
    meal_data[enum_obj] = None

    if enum_obj == UserDataEntry.DESCRIPTION_FOR_AI:
        await dialog_utils.no_markup_message(update, "Text description skipped")
    elif enum_obj == UserDataEntry.IMAGE_FILE:
        await dialog_utils.no_markup_message(update, "Image skipped")
    else:
        await dialog_utils.no_markup_message(update, "Unexpected data key skipped: " + repr(enum_obj))

    if UserDataEntry.DESCRIPTION_FOR_AI not in meal_data:
        await new_meal_utils.ask_for_description(update, meal_data)
        return NewMealStages.ADD_DESCRIPTION_FOR_AI
    elif UserDataEntry.IMAGE_FILE not in meal_data:
        await new_meal_utils.ask_for_picture(update, meal_data)
        return NewMealStages.ADD_IMAGE_FOR_AI
    else:
        await process_ai_request(update, context)
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def process_ai_request(update, context):
    await dialog_utils.no_markup_message(update, "got data for ai")
    meal_data = context.user_data[MEAL_DATA]
    description = meal_data.get(UserDataEntry.DESCRIPTION_FOR_AI, None)
    image = meal_data.get(UserDataEntry.IMAGE_FILE, None)
    await dialog_utils.no_markup_message(update, "Description: " + str(description))
    await dialog_utils.no_markup_message(update, "Image: " + str(image))

    print("description", description)
    print("image", image)


async def handle_confirm_ai_estimate(update, context):
    meal_data = context.user_data[MEAL_DATA]
    choice = update.message.text
    if choice == ConfirmAiOption.CONFIRM:
        return handle_new_meal_data(update, context)
    elif choice == ConfirmAiOption.EXTRA_MESSAGE:
        pass  # TODO
    elif choice == ConfirmAiOption.REENTER_MANUALLY:
        await new_meal_utils.ask_to_confirm_existing_description(update, meal_data)
        return NewMealStages.CONFIRM_EXISTING_NAME_DESCRIPTION
    elif choice == ConfirmAiOption.CANCEL:
        await handle_cancel(update, context)
        return ConversationHandler.END
    else:
        await dialog_utils.wrong_value_message(update)
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def handle_describe_manually(update, context):
    meal_data = context.user_data[MEAL_DATA]
    lines = update.message.text.split("\n", 1)
    name = lines[0]
    description = lines[1] if len(lines) > 1 else ""

    meal_data[UserDataEntry.MEAL_NAME] = name
    meal_data[UserDataEntry.MEAL_DESCRIPTION] = description

    if UserDataEntry.NUTRITION_DATA in meal_data:
        await new_meal_utils.ask_to_confirm_existing_nutrition(update, meal_data)
        return NewMealStages.CONFIRM_EXISTING_NUTRITION
    else:
        await new_meal_utils.ask_for_nutrition_values(update)
        return NewMealStages.ADD_NUTRITION_VALUES_MANUALLY


async def handle_confirm_existing_description(update, context):
    meal_data = context.user_data[MEAL_DATA]
    decision = update.message.text
    if decision == KeepUpdateOption.UPDATE.value:
        await new_meal_utils.ask_for_meal_description(update)
        return NewMealStages.DESCRIBE_MEAL_MANUALLY
    elif decision == KeepUpdateOption.KEEP.value:
        await new_meal_utils.ask_to_confirm_existing_nutrition(update, meal_data)
        return NewMealStages.CONFIRM_EXISTING_NUTRITION
    else:
        # assume user entered new value for the name and description
        await handle_describe_manually(update, context)
        return NewMealStages.CONFIRM_EXISTING_NUTRITION


async def handle_add_nutrition_manually(update, context):
    meal_data = context.user_data[MEAL_DATA]
    nutrition_text = update.message.text
    nutrition_data = new_meal_utils.parse_nutrition_message(
        nutrition_text
    )

    if nutrition_data is None:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.ask_for_nutrition_values(update)
        return NewMealStages.ADD_NUTRITION_VALUES_MANUALLY

    meal_data[UserDataEntry.NUTRITION_DATA] = nutrition_data
    await new_meal_utils.ask_to_confirm_manual_entry_data(
        update, meal_data, long_nutrition=True
    )
    return NewMealStages.CONFIRM_MANUAL_DATA


async def handle_confirm_existing_nutrition(update, context):
    meal_data = context.user_data[MEAL_DATA]
    decision = update.message.text
    if decision == KeepUpdateOption.UPDATE.value:
        await new_meal_utils.ask_for_nutrition_values(update)
        return NewMealStages.ADD_NUTRITION_VALUES_MANUALLY
    elif decision == KeepUpdateOption.KEEP.value:
        await new_meal_utils.ask_to_confirm_manual_entry_data(
            update, meal_data, long_nutrition=True
        )
        return NewMealStages.CONFIRM_MANUAL_DATA
    else:
        # assume user entered new nutrition values
        await handle_add_nutrition_manually(update, context)
        return NewMealStages.CONFIRM_MANUAL_DATA


async def handle_confirm_manual_entry_data(update, context):
    meal_data = context.user_data[MEAL_DATA]
    choice = update.message.text
    if choice == ConfirmManualOption.CONFIRM.value:
        await handle_new_meal_data(update, context)
        return ConversationHandler.END
    elif choice == ConfirmManualOption.REENTER_MANUALLY.value:
        await new_meal_utils.ask_to_confirm_existing_description(
            update, meal_data
        )
        return NewMealStages.CONFIRM_EXISTING_NAME_DESCRIPTION
    elif choice == ConfirmAiOption.CANCEL.value:
        await handle_cancel(update, context)
        return ConversationHandler.END
    else:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.ask_to_confirm_manual_entry_data(
            update, meal_data, long_nutrition=True
        )
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def handle_new_meal_data(update, context):
    meal_data = context.user_data[MEAL_DATA]
    await dialog_utils.no_markup_message(
        update, "Adding new meal with data"
    )
    await dialog_utils.no_markup_message(
        update, new_meal_utils.meal_data_to_string(
            meal_data, long_nutrition=True
        )
    )
    await dialog_utils.no_markup_message(
        update, "New meal added"
    )


async def handle_cancel(update, context):
    await update.message.reply_text(
        "New meal entry cancelled",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


