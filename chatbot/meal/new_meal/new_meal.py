from telegram.ext import filters
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler
from chatbot.config import Commands
from enum import Enum, auto
from chatbot.meal.new_meal import new_meal_utils
from chatbot.meal.new_meal.new_meal_utils import (
    MEAL_DATA, MealDataEntry, InputMode, InlineKeyData,
    ConfirmAiOption, ConfirmManualOption, KeepUpdateOption
)
from database import common_sql
from database.food_database_model import MealEaten
from database.select import select_users
from database.update import update_meals
from chatbot import dialog_utils
from ai_interface import openai_meal_chat
import logging
import traceback

logger = logging.getLogger(__name__)


class NewMealStages(Enum):
    CHOOSE_INPUT_MODE = auto()

    ADD_DATA_FOR_AI = auto()
    ADD_IMAGE_FOR_AI = auto()
    ADD_DESCRIPTION_FOR_AI = auto()
    CONFIRM_AI_ESTIMATE = auto()
    ADD_MORE_INFO_FOR_AI = auto()

    DESCRIBE_MEAL_MANUALLY = auto()
    CHOOSE_ENTER_ONE_OR_MANY_INGREDIENTS = auto()
    ADD_NUTRITION_SINGLE_ENTRY_MANUALLY = auto()
    ADD_NUTRITION_MULTIPLE_ENTRIES_MANUALLY = auto()
    ADD_MORE_INGREDIENTS_OR_FINISH = auto()
    CONFIRM_FULL_DATA_MANUAL_ENTRY = auto()

    CONFIRM_EXISTING_NAME_DESCRIPTION = auto()
    CONFIRM_EXISTING_NUTRITION = auto()

    CHOOSE_TO_SAVE_MEAL_FOR_FUTURE_USE = auto()
    ENTER_CORRECTED_WEIGHT = auto()


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
            CallbackQueryHandler(callback=skip_description_callback)
        ],
        NewMealStages.ADD_DESCRIPTION_FOR_AI: [
            MessageHandler(text_only_filter, handle_describe_for_ai),
            CallbackQueryHandler(callback=skip_description_callback)
        ],
        NewMealStages.CONFIRM_AI_ESTIMATE: [
            MessageHandler(text_only_filter, handle_confirm_ai_estimate)
        ],
        NewMealStages.ADD_MORE_INFO_FOR_AI: [
            MessageHandler(text_only_filter, handle_more_info_for_ai)
        ],
        NewMealStages.DESCRIBE_MEAL_MANUALLY: [
            MessageHandler(text_only_filter, handle_describe_manually)
        ],
        NewMealStages.CHOOSE_ENTER_ONE_OR_MANY_INGREDIENTS: [
            MessageHandler(text_only_filter, handle_choose_one_or_many_ingredients)
        ],
        NewMealStages.ADD_NUTRITION_SINGLE_ENTRY_MANUALLY: [
            MessageHandler(text_only_filter, handle_add_nutrition_single_entry)
        ],
        NewMealStages.ADD_NUTRITION_MULTIPLE_ENTRIES_MANUALLY: [
            MessageHandler(text_only_filter, handle_add_nutrition_one_of_multiple)
        ],
        NewMealStages.ADD_MORE_INGREDIENTS_OR_FINISH: [
            MessageHandler(text_only_filter, handle_choose_more_ingredients_or_finish)
        ],
        NewMealStages.CONFIRM_FULL_DATA_MANUAL_ENTRY: [
            MessageHandler(text_only_filter, handle_confirm_manual_entry_data)
        ],
        NewMealStages.CONFIRM_EXISTING_NAME_DESCRIPTION: [
            MessageHandler(text_only_filter, handle_confirm_existing_description_manual_entry)
        ],
        NewMealStages.CONFIRM_EXISTING_NUTRITION: [
            MessageHandler(text_only_filter, handle_confirm_existing_nutrition_manual_entry)
        ],
        NewMealStages.CHOOSE_TO_SAVE_MEAL_FOR_FUTURE_USE: [
            MessageHandler(text_only_filter, handle_confirm_save_meal_for_future_use)
        ],
        NewMealStages.ENTER_CORRECTED_WEIGHT: [
            MessageHandler(text_only_filter, handle_corrected_weight),
            CallbackQueryHandler(callback=skip_save_for_future_use_callback)
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
    meal_dialog_data = context.user_data[MEAL_DATA]

    with common_sql.get_session() as session:
        existing_user = select_users.select_user_by_telegram_id(
            session, update.message.from_user.id
        )

    if existing_user is None:
        return await dialog_utils.user_does_not_exist_message(update)

    meal_dialog_data[MealDataEntry.USER_NAME] = existing_user.name
    meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT] = MealEaten(
        user_id=existing_user.id
    )

    await update.message.reply_text(
        f"Hi {meal_dialog_data[MealDataEntry.USER_NAME]}! Let's add a new meal. \n",
        reply_markup=ReplyKeyboardRemove()
    )
    await new_meal_utils.input_mode_question(update)
    return NewMealStages.CHOOSE_INPUT_MODE


async def handle_choose_input_mode(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]

    input_mode = update.message.text
    if input_mode not in InputMode:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.input_mode_question(update)
        return NewMealStages.CHOOSE_INPUT_MODE

    meal_dialog_data[MealDataEntry.IS_USING_AI] = (input_mode == InputMode.AI)

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
    meal_dialog_data = context.user_data[MEAL_DATA]
    await new_meal_utils.remove_last_skip_button(context, meal_dialog_data)

    description = update.message.text
    description = description.strip()
    meal_dialog_data[MealDataEntry.DESCRIPTION_FOR_AI] = description
    if MealDataEntry.IMAGE_DATA_FOR_AI not in meal_dialog_data:
        await new_meal_utils.ask_for_image(update, meal_dialog_data)
        return NewMealStages.ADD_IMAGE_FOR_AI
    else:
        await process_ai_request(update, context)
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def handle_image_for_ai(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    await new_meal_utils.remove_last_skip_button(context, meal_dialog_data)

    caption = update.message.caption
    images_different_res = update.message.photo

    if len(images_different_res) == 0:
        await dialog_utils.no_markup_message(update, "Failed to get an image")
        await new_meal_utils.ask_for_image(update, meal_dialog_data)
        return NewMealStages.ADD_IMAGE_FOR_AI

    image_highest_res = images_different_res[-1]
    image_data = await new_meal_utils.telegram_photo_obj_to_image_data(
        image_highest_res
    )

    if MealDataEntry.IMAGE_DATA_FOR_AI in meal_dialog_data:
        await dialog_utils.no_markup_message(
            update, "Multiple images received. Using the latest message."
        )

    meal_dialog_data[MealDataEntry.IMAGE_DATA_FOR_AI] = image_data

    # use caption as description
    # if description data was not specified
    # or was explicitly skipped (is None check)
    if caption is not None and (
            meal_dialog_data.get(MealDataEntry.DESCRIPTION_FOR_AI, None) is None
    ):
        meal_dialog_data[MealDataEntry.DESCRIPTION_FOR_AI] = caption

    if MealDataEntry.DESCRIPTION_FOR_AI not in meal_dialog_data:
        await new_meal_utils.ask_for_description(update, meal_dialog_data)
        return NewMealStages.ADD_DESCRIPTION_FOR_AI
    else:
        await process_ai_request(update, context)
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def skip_description_callback(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_reply_markup(None)

    meal_dialog_data = context.user_data[MEAL_DATA]
    data = update.callback_query.data
    try:
        data_key = MealDataEntry[data]
        meal_dialog_data[data_key] = None
    except KeyError:
        await dialog_utils.no_markup_message(
            update, "Unexpected data received: " + data
        )

    if data == InlineKeyData.DESCRIPTION_FOR_AI.value:
        await dialog_utils.no_markup_message(update, "Text description skipped")
    elif data == InlineKeyData.IMAGE_DATA_FOR_AI.value:
        await dialog_utils.no_markup_message(update, "Image skipped")
    else:
        await dialog_utils.no_markup_message(
            update, "Unexpected data received: " + data
        )

    if MealDataEntry.DESCRIPTION_FOR_AI not in meal_dialog_data:
        await new_meal_utils.ask_for_description(update, meal_dialog_data)
        return NewMealStages.ADD_DESCRIPTION_FOR_AI
    elif MealDataEntry.IMAGE_DATA_FOR_AI not in meal_dialog_data:
        await new_meal_utils.ask_for_image(update, meal_dialog_data)
        return NewMealStages.ADD_IMAGE_FOR_AI
    else:
        await process_ai_request(update, context)
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def process_ai_request(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    description = meal_dialog_data.get(MealDataEntry.DESCRIPTION_FOR_AI, None)
    image_data = meal_dialog_data.get(MealDataEntry.IMAGE_DATA_FOR_AI, None)

    try:
        await dialog_utils.no_markup_message(update, "Sending request to AI...\nPlease wait")
        ai_response = openai_meal_chat.get_meal_estimate(
            description, image_data
        )
    except Exception as e:
        logger.error(f"get_meal_estimate exception: {e}" + "\n" + f"{traceback.format_exc()}")
        message = f"Error!\n Internal function get_meal_estimate exception\n{e}"
        await dialog_utils.no_markup_message(update, message)
        return await handle_cancel(update, context)

    new_data_added = await new_meal_utils.handle_new_ai_response(
        ai_response, update, meal_dialog_data
    )
    if not new_data_added:
        # error was printed by handle_new_ai_response
        await new_meal_utils.input_mode_question(update)
        return NewMealStages.CHOOSE_INPUT_MODE
    else:
        await new_meal_utils.ask_to_confirm_ai_estimate(update, meal_dialog_data)
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def handle_confirm_ai_estimate(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    choice = update.message.text
    if choice == ConfirmAiOption.CONFIRM.value:
        await new_meal_utils.ask_to_save_meal_for_future_use(update)
        return NewMealStages.CHOOSE_TO_SAVE_MEAL_FOR_FUTURE_USE
    elif choice == ConfirmAiOption.MORE_INFO.value:
        await new_meal_utils.ask_for_mode_information(update)
        return NewMealStages.ADD_MORE_INFO_FOR_AI
    elif choice == ConfirmAiOption.REENTER_MANUALLY.value:
        # start the sequence of existing data confirmation
        # with an option to manually change it
        await new_meal_utils.ask_to_confirm_existing_description(update, meal_dialog_data)
        return NewMealStages.CONFIRM_EXISTING_NAME_DESCRIPTION
    elif choice == ConfirmAiOption.CANCEL.value:
        return await handle_cancel(update, context)
    else:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.ask_to_confirm_ai_estimate(
            update, meal_dialog_data, show_estimates=False
        )
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def handle_more_info_for_ai(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    extra_info = update.message.text
    prev_ai_messages = meal_dialog_data[MealDataEntry.LAST_AI_MESSAGE_LIST]

    try:
        await dialog_utils.no_markup_message(update, "Sending request to AI...\nPlease wait")
        ai_response = openai_meal_chat.update_meal_estimate(
            prev_ai_messages, extra_info
        )
    except Exception as e:
        logger.error(f"update_meal_estimate exception: {e}" + "\n" + f"{traceback.format_exc()}")
        message = f"Error!\n Internal function update_meal_estimate exception\n{e}"
        await dialog_utils.no_markup_message(update, message)
        return await handle_cancel(update, context)

    new_data_added = await new_meal_utils.handle_new_ai_response(
        ai_response, update, meal_dialog_data
    )
    if not new_data_added:
        await dialog_utils.no_markup_message(
            update, "You can try and send another text message"
        )
        return NewMealStages.ADD_MORE_INFO_FOR_AI
    else:
        await new_meal_utils.ask_to_confirm_ai_estimate(update, meal_dialog_data)
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def handle_describe_manually(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    lines = update.message.text.split("\n", 1)
    name = lines[0]
    description = lines[1] if len(lines) > 1 else ""

    meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]

    meal.name = name
    meal.description = description

    if meal.calories is not None:
        await new_meal_utils.ask_to_confirm_existing_nutrition(update, meal_dialog_data)
        return NewMealStages.CONFIRM_EXISTING_NUTRITION
    else:
        await new_meal_utils.ask_one_or_many_ingredients_to_enter(update)
        return NewMealStages.CHOOSE_ENTER_ONE_OR_MANY_INGREDIENTS


async def handle_choose_one_or_many_ingredients(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    decision = update.message.text

    if decision == new_meal_utils.OneMultipleIngredients.ONE.value:
        await new_meal_utils.ask_for_single_entry_nutrition(update)
        return NewMealStages.ADD_NUTRITION_SINGLE_ENTRY_MANUALLY
    elif decision == new_meal_utils.OneMultipleIngredients.MULTIPLE.value:
        await new_meal_utils.ask_for_multiple_ingredients_nutrition(update)
        await new_meal_utils.ask_for_next_ingredient(update, meal_dialog_data)
        return NewMealStages.ADD_NUTRITION_MULTIPLE_ENTRIES_MANUALLY
    else:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.ask_one_or_many_ingredients_to_enter(update)
        return NewMealStages.CHOOSE_ENTER_ONE_OR_MANY_INGREDIENTS


async def handle_add_nutrition_single_entry(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    nutrition_text = update.message.text
    nutrition_data = new_meal_utils.parse_nutrition_message(
        nutrition_text
    )

    if nutrition_data is None:
        await dialog_utils.wrong_value_message(update, "Nutrition string parsing failed.")
        await new_meal_utils.ask_for_single_entry_nutrition(update, format_only=True)
        return NewMealStages.ADD_NUTRITION_SINGLE_ENTRY_MANUALLY

    meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]
    new_meal_utils.assign_nutrition_values_from_dict(
        meal, nutrition_data
    )

    await new_meal_utils.ask_to_confirm_manual_entry_data(
        update, meal_dialog_data, long_nutrition=True
    )
    return NewMealStages.CONFIRM_FULL_DATA_MANUAL_ENTRY


async def handle_add_nutrition_one_of_multiple(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    ingredients_nutrition_value = meal_dialog_data.get(MealDataEntry.INGREDIENT_NUTRITION_DATA, [])
    input_text = update.message.text
    input_lines = input_text.split("\n")
    if len(input_lines) < 2:
        name = None
        nutrition_line = input_lines[0]
    else:
        name = input_lines[0]
        nutrition_line = input_lines[1]
    nutrition_data = new_meal_utils.parse_nutrition_message(
        nutrition_line
    )
    if nutrition_data is None:
        await dialog_utils.wrong_value_message(update, "Nutrition string parsing failed.")
        await new_meal_utils.ask_for_multiple_ingredients_nutrition(update, format_only=True)
        return NewMealStages.ADD_NUTRITION_MULTIPLE_ENTRIES_MANUALLY

    ingredients_nutrition_value.append((name, nutrition_data))
    meal_dialog_data[MealDataEntry.INGREDIENT_NUTRITION_DATA] = ingredients_nutrition_value
    await dialog_utils.no_markup_message(update, "Added")
    await new_meal_utils.ask_more_ingredients_or_finish(update)
    return NewMealStages.ADD_MORE_INGREDIENTS_OR_FINISH


async def handle_choose_more_ingredients_or_finish(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    decision = update.message.text

    if decision == new_meal_utils.MoreIngredientsOrFinish.MORE.value:
        await new_meal_utils.ask_for_next_ingredient(update, meal_dialog_data)
        return NewMealStages.ADD_NUTRITION_MULTIPLE_ENTRIES_MANUALLY
    elif decision == new_meal_utils.MoreIngredientsOrFinish.FINISH.value:
        await new_meal_utils.describe_ingredients(update, meal_dialog_data, include_total=False)
        new_meal_utils.combine_ingredients(meal_dialog_data)
        await new_meal_utils.ask_to_confirm_manual_entry_data(
            update, meal_dialog_data, long_nutrition=True
        )
        return NewMealStages.CONFIRM_FULL_DATA_MANUAL_ENTRY
    else:
        # assume this is a new ingredient entry
        return await handle_add_nutrition_one_of_multiple(update, context)


async def handle_confirm_existing_description_manual_entry(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    decision = update.message.text
    if decision == KeepUpdateOption.UPDATE.value:
        await new_meal_utils.ask_for_meal_description(update)
        return NewMealStages.DESCRIBE_MEAL_MANUALLY
    elif decision == KeepUpdateOption.KEEP.value:
        await new_meal_utils.ask_to_confirm_existing_nutrition(update, meal_dialog_data)
        return NewMealStages.CONFIRM_EXISTING_NUTRITION
    else:
        # assume user entered new value for the name and description
        await handle_describe_manually(update, context)
        return NewMealStages.CONFIRM_EXISTING_NUTRITION


async def handle_confirm_existing_nutrition_manual_entry(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    decision = update.message.text
    if decision == KeepUpdateOption.UPDATE.value:
        await new_meal_utils.ask_one_or_many_ingredients_to_enter(update)
        return NewMealStages.CHOOSE_ENTER_ONE_OR_MANY_INGREDIENTS
    elif decision == KeepUpdateOption.KEEP.value:
        await new_meal_utils.ask_to_confirm_manual_entry_data(
            update, meal_dialog_data, long_nutrition=True
        )
        return NewMealStages.CONFIRM_FULL_DATA_MANUAL_ENTRY
    else:
        # assume user entered new nutrition values
        await handle_add_nutrition_single_entry(update, context)
        return NewMealStages.CONFIRM_FULL_DATA_MANUAL_ENTRY


async def handle_confirm_manual_entry_data(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    choice = update.message.text
    if choice == ConfirmManualOption.CONFIRM.value:
        await new_meal_utils.ask_to_save_meal_for_future_use(update)
        return NewMealStages.CHOOSE_TO_SAVE_MEAL_FOR_FUTURE_USE
    elif choice == ConfirmManualOption.REENTER.value:
        await new_meal_utils.ask_to_confirm_existing_description(
            update, meal_dialog_data
        )
        return NewMealStages.CONFIRM_EXISTING_NAME_DESCRIPTION
    elif choice == ConfirmAiOption.CANCEL.value:
        return await handle_cancel(update, context)
    else:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.ask_to_confirm_manual_entry_data(
            update, meal_dialog_data, long_nutrition=True
        )
        return NewMealStages.CONFIRM_FULL_DATA_MANUAL_ENTRY


async def handle_confirm_save_meal_for_future_use(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    confirm = update.message.text
    if confirm not in dialog_utils.YesNo:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.ask_to_save_meal_for_future_use(update)

    save_for_future_use = (confirm == dialog_utils.YesNo.YES.value)

    if save_for_future_use:
        meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]
        if meal.weight > 0:
            meal_dialog_data[MealDataEntry.SAVE_FOR_FUTURE_USE] = True
        else:
            await new_meal_utils.ask_for_positive_weight(update, meal_dialog_data)
            return NewMealStages.ENTER_CORRECTED_WEIGHT
    else:
        meal_dialog_data[MealDataEntry.SAVE_FOR_FUTURE_USE] = False

    return await handle_new_meal_data(update, context)


async def skip_save_for_future_use_callback(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_reply_markup(None)

    meal_dialog_data = context.user_data[MEAL_DATA]

    callback_data = update.callback_query.data

    if callback_data == InlineKeyData.SKIP_SAVING_FOR_FUTURE_USE.value:
        await dialog_utils.no_markup_message(update, "Saving for future use skipped")
        meal_dialog_data[MealDataEntry.SAVE_FOR_FUTURE_USE] = False
        return await handle_new_meal_data(update, context)
    else:
        await dialog_utils.no_markup_message(update, "Unexpected data received: " + callback_data)
        await new_meal_utils.ask_for_positive_weight(update, new_meal_utils)
        return NewMealStages.ENTER_CORRECTED_WEIGHT


async def handle_corrected_weight(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    await new_meal_utils.remove_last_skip_button(context, meal_dialog_data)

    new_weight = new_meal_utils.parse_float(update.message.text)

    if new_weight is None or new_weight < 0:
        await new_meal_utils.ask_for_positive_weight(update, meal_dialog_data)
        return NewMealStages.ENTER_CORRECTED_WEIGHT
    else:
        meal_dialog_data[MealDataEntry.SAVE_FOR_FUTURE_USE] = True
        meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]
        meal.weight = new_weight
        return await handle_new_meal_data(update, context)


async def handle_new_meal_data(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    meal: MealEaten = meal_dialog_data[MealDataEntry.NEW_MEAL_OBJECT]
    save_for_future_use = meal_dialog_data[MealDataEntry.SAVE_FOR_FUTURE_USE]

    await dialog_utils.no_markup_message(
        update, "Creating new meal"
    )

    try:
        with common_sql.get_session() as session:
            update_meals.add_new_eaten_meal(session, meal)
            await dialog_utils.no_markup_message(update, "New meal added")
            await dialog_utils.no_markup_message(update, meal.describe())

            if save_for_future_use:
                update_meals.add_new_meal_for_future_use_from_meal_eaten(
                    session, meal
                )
                await dialog_utils.no_markup_message(
                    update, "New meal saved for future use"
                )

    except Exception as e:
        logging.exception(e)
        await dialog_utils.no_markup_message(
            update, "Database error"
        )

    return ConversationHandler.END


async def handle_cancel(update, context):
    meal_dialog_data = context.user_data[MEAL_DATA]
    await new_meal_utils.remove_last_skip_button(context, meal_dialog_data)
    message = "New meal entry cancelled"
    await update.message.reply_text(
        message, reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END
