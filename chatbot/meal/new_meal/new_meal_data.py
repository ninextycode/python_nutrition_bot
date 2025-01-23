from telegram.ext import filters
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler
from chatbot.config import Commands
from enum import Enum, auto
from chatbot.meal.new_meal import new_meal_utils
from chatbot.meal.new_meal.new_meal_utils import (
    MealDataEntry, InputMode, NewMealInlineDataKey, TimeIsNowDataKey,
    ConfirmAiOption, ConfirmManualOption, KeepUpdateOption, SkipDescriptionBtnValue, EditMode, MealDataMode
)
from chatbot.config import DataKeys
from chatbot.parent_child_utils import pop_parent_data, ConversationID, ChildEndStage
from chatbot.start_menu import start_menu_utils
from database import common_sql
from database.common_sql import get_session
from database.food_database_model import MealEaten, User
from database.update import update_meals
from database.select import select_meals
from chatbot import dialog_utils
from chatbot.inline_key_utils import (
    InlineButtonDataKeyValue, StartConversationDataKey
)
from ai_interface import openai_meal_chat
import logging
import traceback
import datetime
import dateparser
from chatbot.meal.meals_dataview import meals_dataview_utils


logger = logging.getLogger(__name__)


class NewMealStages(Enum):
    ADD_MEAL_TIME = auto()

    CHOOSE_INPUT_MODE = auto()
    CHOOSE_EDIT_MODE = auto()

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
        CommandHandler(Commands.NEW_MEAL.value, handle_new_meal_command),
        CallbackQueryHandler(
            callback=handle_new_meal_inline_callback,
            pattern=StartConversationDataKey.NEW_MEAL.to_str()
        ),
        CallbackQueryHandler(
            callback=handle_edit_meal_inline_callback,
            pattern=StartConversationDataKey.EDIT_MEAL.to_str()
        )
    ]
    states = {
        NewMealStages.ADD_MEAL_TIME: [
            MessageHandler(text_only_filter, handle_meal_time),
            CallbackQueryHandler(
                time_is_now_callback,
                pattern=TimeIsNowDataKey.TIME_IS_NOW.to_str()
            ),
        ],
        NewMealStages.CHOOSE_INPUT_MODE: [
            MessageHandler(text_only_filter, handle_choose_input_mode),
            MessageHandler(filters.PHOTO, handle_assume_image_for_ai),
        ],
        NewMealStages.ADD_DATA_FOR_AI: [
            MessageHandler(text_only_filter, handle_describe_for_ai),
            MessageHandler(filters.PHOTO, handle_image_for_ai),
        ],
        NewMealStages.ADD_IMAGE_FOR_AI: [
            MessageHandler(filters.PHOTO, handle_image_for_ai),
            CallbackQueryHandler(
                callback=skip_description_callback,
                pattern=NewMealInlineDataKey.SKIP_DESCRIPTION_FOR_AI.to_str()
            )
        ],
        NewMealStages.ADD_DESCRIPTION_FOR_AI: [
            MessageHandler(text_only_filter, handle_describe_for_ai),
            CallbackQueryHandler(
                callback=skip_description_callback,
                pattern=NewMealInlineDataKey.SKIP_DESCRIPTION_FOR_AI.to_str()
            )
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
            CallbackQueryHandler(
                callback=skip_save_for_future_use_callback,
                pattern=NewMealInlineDataKey.SKIP_SAVING_FOR_FUTURE_USE.to_str()
            )
        ]
    }
    # allows to restart dialog from the middle
    for k in states.keys():
        states[k].extend(entry_points)

    fallbacks = [
        CommandHandler(Commands.CANCEL.value, handle_cancel)
    ]
    handler = ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=fallbacks,
        map_to_parent={
            ConversationHandler.END: ChildEndStage.NEW_MEAL_END
        }
    )
    return handler


async def init_meal_dialog_data(update, context):
    if DataKeys.MEAL_DATA in context.user_data:
        await new_meal_utils.remove_last_skip_button(
            context, context.user_data[DataKeys.MEAL_DATA]
        )
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA] = dict()
    user = dialog_utils.get_tg_user_obj(update)
    if user is None:
        await dialog_utils.user_does_not_exist_message(update)
        raise RuntimeError("User does not exist")

    meal_dialog_data[MealDataEntry.USER] = user



async def handle_new_meal_inline_callback(update, context):
    await dialog_utils.handle_inline_keyboard_callback(
        update, delete_keyboard=True
    )

    await init_meal_dialog_data(update, context)

    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    data_str = update.callback_query.data

    data_value = InlineButtonDataKeyValue.from_str(data_str).value

    parent_id = ConversationID(data_value)
    meal_dialog_data[MealDataEntry.PARENT_ID] = parent_id

    if parent_id == ConversationID.DAY_VIEW:
        date = pop_parent_data(context, parent_id, ConversationID.NEW_MEAL)
        meal_dialog_data[MealDataEntry.MEAL_DATE] = date
        if not isinstance(date, datetime.date):
            logger.warning(
                "new_meal is a child conversation\n"
                "callback data object for new_meal conversation exists, "
                f"but parent data = {date}, expected datetime.date"
            )
    else:
        user: User = meal_dialog_data[MealDataEntry.USER]
        meal_dialog_data[MealDataEntry.MEAL_DATE] = user.get_datetime_now().date()

    return await start_new_meal(update, context)


async def handle_new_meal_command(update, context):
    await init_meal_dialog_data(update, context)
    return await start_new_meal(update, context)


async def start_new_meal(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    meal_dialog_data[MealDataEntry.DATA_MODE] = MealDataMode.NEW
    user = meal_dialog_data[MealDataEntry.USER]
    new_meal = MealEaten(user_id=user.id)
    meal_dialog_data[MealDataEntry.MEAL_OBJECT] = new_meal

    await dialog_utils.no_markup_message(
        update,
        f"Hi {meal_dialog_data[MealDataEntry.USER].name}! Let's add a new meal. \n",
    )

    custom_date = meal_dialog_data.get(MealDataEntry.MEAL_DATE, None)
    await new_meal_utils.ask_time_of_meal(update, user, custom_date)
    return NewMealStages.ADD_MEAL_TIME


async def handle_meal_time(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]

    time_s = update.message.text
    dt_parsed = dateparser.parse(time_s)

    if dt_parsed is None:
        await dialog_utils.wrong_value_message(update, "Cannot determine time")
        existing_user = meal_dialog_data[MealDataEntry.USER]
        date = meal_dialog_data[MealDataEntry.MEAL_DATE]
        await new_meal_utils.ask_time_of_meal(update, existing_user, date)
        return NewMealStages.ADD_MEAL_TIME

    time = dt_parsed.time()
    date = meal_dialog_data[MealDataEntry.MEAL_DATE]
    dt = datetime.datetime.combine(date, time)

    new_meal = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
    new_meal.created_local_datetime = dt

    await new_meal_utils.ask_input_mode(update)
    return NewMealStages.CHOOSE_INPUT_MODE


async def time_is_now_callback(update, context):
    await dialog_utils.handle_inline_keyboard_callback(
        update, delete_keyboard=True
    )

    data = InlineButtonDataKeyValue.from_str(update.callback_query.data)
    time_now = datetime.datetime.strptime(data.value, "%H:%M").time()

    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    date = meal_dialog_data[MealDataEntry.MEAL_DATE]

    dt = datetime.datetime.combine(date, time_now)

    new_meal = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
    new_meal.created_local_datetime = dt
    await dialog_utils.no_markup_message(
        update,
        "Meal time is " + time_now.strftime("%H:%M")
    )
    await new_meal_utils.ask_input_mode(update)
    return NewMealStages.CHOOSE_INPUT_MODE


async def handle_choose_input_mode(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]

    new_meal_utils.reset_ai_data(meal_dialog_data)

    input_mode = update.message.text

    if input_mode == InputMode.AI.value:
        await new_meal_utils.ask_ai_input(update)
        return NewMealStages.ADD_DATA_FOR_AI

    elif input_mode == InputMode.MANUAL.value:
        await new_meal_utils.ask_for_meal_description(update)
        return NewMealStages.DESCRIBE_MEAL_MANUALLY

    elif input_mode == InputMode.BARCODE.value:
        await dialog_utils.wrong_value_message(update, "not implemented")
        await new_meal_utils.ask_input_mode(update)
        return NewMealStages.CHOOSE_INPUT_MODE
    else:
        # assume input is a description for AI
        return await handle_assume_describe_for_ai(update, context)


async def handle_assume_describe_for_ai(update, context):
    await dialog_utils.no_markup_message(update, f"Assuming input for AI")
    return await handle_describe_for_ai(update, context)


async def handle_describe_for_ai(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    await new_meal_utils.remove_last_skip_button(context, meal_dialog_data)

    description = update.message.text
    description = description.strip()
    meal_dialog_data[MealDataEntry.DESCRIPTION_FOR_AI] = description
    if MealDataEntry.IMAGE_DATA_FOR_AI not in meal_dialog_data:
        await new_meal_utils.ask_for_image(update, meal_dialog_data)
        return NewMealStages.ADD_IMAGE_FOR_AI
    else:
        return  await process_ai_request(update, context)


async def handle_assume_image_for_ai(update, context):
    await dialog_utils.no_markup_message(update, f"Assuming input for AI")
    return await handle_image_for_ai(update, context)


async def handle_image_for_ai(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
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
        return await process_ai_request(update, context)


async def skip_description_callback(update, context):
    await dialog_utils.handle_inline_keyboard_callback(
        update, delete_keyboard=True
    )

    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    data = InlineButtonDataKeyValue.from_str(update.callback_query.data)

    if data.value == SkipDescriptionBtnValue.DESCRIPTION_FOR_AI.value:
        meal_dialog_data[MealDataEntry.DESCRIPTION_FOR_AI] = None
        await dialog_utils.no_markup_message(update, "Text description skipped")
    elif data.value == SkipDescriptionBtnValue.IMAGE_DATA_FOR_AI.value:
        meal_dialog_data[MealDataEntry.IMAGE_DATA_FOR_AI] = None
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
        return await process_ai_request(update, context)


async def process_ai_request(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
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
        new_meal_utils.reset_ai_data(meal_dialog_data)
        await dialog_utils.no_markup_message(
            update, "Please try again"
        )
        await new_meal_utils.ask_input_mode(update)
        return NewMealStages.CHOOSE_INPUT_MODE
    else:
        await new_meal_utils.ask_to_confirm_ai_estimate(
            update, meal_dialog_data[MealDataEntry.MEAL_OBJECT]
        )
        return NewMealStages.CONFIRM_AI_ESTIMATE


async def handle_confirm_ai_estimate(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    choice = update.message.text
    if choice == ConfirmAiOption.CONFIRM.value:
        await new_meal_utils.ask_to_save_meal_for_future_use(update)
        return NewMealStages.CHOOSE_TO_SAVE_MEAL_FOR_FUTURE_USE
    elif choice == ConfirmAiOption.MORE_INFO.value:
        await new_meal_utils.ask_for_mode_information(update)
        return NewMealStages.ADD_MORE_INFO_FOR_AI
    elif choice == ConfirmAiOption.REENTER_MANUALLY.value:
        # start_menu the sequence of existing data confirmation
        # with an option to manually change it
        await new_meal_utils.ask_to_confirm_existing_description(update, meal_dialog_data)
        return NewMealStages.CONFIRM_EXISTING_NAME_DESCRIPTION
    else:
        # assume the new message is a message with more info for ai
        return await handle_more_info_for_ai(update, context)


async def handle_more_info_for_ai(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
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
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    lines = update.message.text.split("\n", 1)
    name = lines[0]
    description = lines[1] if len(lines) > 1 else ""

    meal: MealEaten = meal_dialog_data[MealDataEntry.MEAL_OBJECT]

    meal.name = name
    meal.description = description

    if meal.calories is not None:
        await new_meal_utils.ask_to_confirm_existing_nutrition(update, meal_dialog_data)
        return NewMealStages.CONFIRM_EXISTING_NUTRITION
    else:
        await new_meal_utils.ask_one_or_many_ingredients_to_enter(update)
        return NewMealStages.CHOOSE_ENTER_ONE_OR_MANY_INGREDIENTS


async def handle_choose_one_or_many_ingredients(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
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
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    nutrition_text = update.message.text
    nutrition_data = dialog_utils.parse_nutrition_message(
        nutrition_text,
    )

    if nutrition_data is None:
        await dialog_utils.wrong_value_message(update, "Nutrition string parsing failed.")
        await new_meal_utils.ask_for_single_entry_nutrition(update, format_only=True)
        return NewMealStages.ADD_NUTRITION_SINGLE_ENTRY_MANUALLY

    meal: MealEaten = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
    new_meal_utils.assign_nutrition_values_from_dict(
        meal, nutrition_data
    )

    await new_meal_utils.ask_to_confirm_manual_entry_data(
        update, meal_dialog_data, long_nutrition=True
    )
    return NewMealStages.CONFIRM_FULL_DATA_MANUAL_ENTRY


async def handle_add_nutrition_one_of_multiple(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    ingredients_nutrition_value = meal_dialog_data.get(
        MealDataEntry.INGREDIENT_NUTRITION_DATA, []
    )
    input_text = update.message.text
    input_lines = input_text.split("\n")
    if len(input_lines) < 2:
        name = None
        nutrition_line = input_lines[0]
    else:
        name = input_lines[0]
        nutrition_line = input_lines[1]
    nutrition_data = dialog_utils.parse_nutrition_message(
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
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    decision = update.message.text

    if decision == new_meal_utils.MoreIngredientsOrFinish.MORE.value:
        await new_meal_utils.ask_for_next_ingredient(update, meal_dialog_data)
        return NewMealStages.ADD_NUTRITION_MULTIPLE_ENTRIES_MANUALLY
    elif decision == new_meal_utils.MoreIngredientsOrFinish.FINISH.value:
        await new_meal_utils.describe_ingredients(
            update, meal_dialog_data, include_total=False
        )
        new_meal_utils.combine_ingredients(meal_dialog_data)
        await new_meal_utils.ask_to_confirm_manual_entry_data(
            update, meal_dialog_data, long_nutrition=True
        )
        return NewMealStages.CONFIRM_FULL_DATA_MANUAL_ENTRY
    else:
        # assume this is a new ingredient entry
        return await handle_add_nutrition_one_of_multiple(update, context)


async def handle_confirm_existing_description_manual_entry(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
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
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    decision = update.message.text
    if decision == KeepUpdateOption.UPDATE.value:
        # when values are adjusted, don't prompt an option with multiple ingredients
        # prompt only nutrition input as single entry
        await new_meal_utils.ask_for_single_entry_nutrition(update)
        return NewMealStages.ADD_NUTRITION_SINGLE_ENTRY_MANUALLY
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
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    choice = update.message.text
    if choice == ConfirmManualOption.CONFIRM.value:
        await new_meal_utils.ask_to_save_meal_for_future_use(update)
        return NewMealStages.CHOOSE_TO_SAVE_MEAL_FOR_FUTURE_USE
    elif choice == ConfirmManualOption.REENTER.value:
        await new_meal_utils.ask_to_confirm_existing_description(
            update, meal_dialog_data
        )
        return NewMealStages.CONFIRM_EXISTING_NAME_DESCRIPTION
    else:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.ask_to_confirm_manual_entry_data(
            update, meal_dialog_data, long_nutrition=True
        )
        return NewMealStages.CONFIRM_FULL_DATA_MANUAL_ENTRY


async def handle_confirm_save_meal_for_future_use(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    confirm = update.message.text
    if confirm not in dialog_utils.YesNo:
        await dialog_utils.wrong_value_message(update)
        await new_meal_utils.ask_to_save_meal_for_future_use(update)

    save_for_future_use = (confirm == dialog_utils.YesNo.YES.value)

    if save_for_future_use:
        meal: MealEaten = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
        if meal.weight > 0:
            meal_dialog_data[MealDataEntry.SAVE_FOR_FUTURE_USE] = True
        else:
            await new_meal_utils.ask_for_positive_weight(update, meal_dialog_data)
            return NewMealStages.ENTER_CORRECTED_WEIGHT
    else:
        meal_dialog_data[MealDataEntry.SAVE_FOR_FUTURE_USE] = False

    return await handle_new_meal_data(update, context)


async def skip_save_for_future_use_callback(update, context):
    await dialog_utils.handle_inline_keyboard_callback(
        update, delete_keyboard=True
    )

    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    await dialog_utils.no_markup_message(
        update, "Saving for future use skipped"
    )
    meal_dialog_data[MealDataEntry.SAVE_FOR_FUTURE_USE] = False
    return await handle_new_meal_data(update, context)


async def handle_corrected_weight(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    await new_meal_utils.remove_last_skip_button(context, meal_dialog_data)

    try:
        new_weight = float(update.message.text)
    except ValueError:
        return None

    if new_weight is None or new_weight < 0:
        await new_meal_utils.ask_for_positive_weight(update, meal_dialog_data)
        return NewMealStages.ENTER_CORRECTED_WEIGHT
    else:
        meal_dialog_data[MealDataEntry.SAVE_FOR_FUTURE_USE] = True
        meal: MealEaten = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
        meal.weight = new_weight
        return await handle_new_meal_data(update, context)


async def handle_new_meal_data(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    meal: MealEaten = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
    save_for_future_use = meal_dialog_data[MealDataEntry.SAVE_FOR_FUTURE_USE]

    await dialog_utils.no_markup_message(
        update, "Creating new meal"
    )

    try:
        with common_sql.get_session() as session:
            if save_for_future_use:
                update_meals.add_new_meal_for_future_use_from_meal_eaten(
                    session, meal
                )
                await dialog_utils.no_markup_message(
                    update, "New meal saved for future use"
                )

            update_meals.add_new_eaten_meal(session, meal)
            await new_meal_utils.new_meal_added_message(
                update, meal,
                # offer to transfer to meal view dialog only if this is not a child conversation
                # ie does not have a parent
                view_meals_inline_btn=MealDataEntry.PARENT_ID not in meal_dialog_data
            )

    except Exception as e:
        logging.exception(e)
        await dialog_utils.no_markup_message(
            update, "Database error"
        )

    return await end_conversation(update, context)


async def handle_cancel(update, context):
    meal_dialog_data = context.user_data.get(DataKeys.MEAL_DATA, dict())
    await new_meal_utils.remove_last_skip_button(context, meal_dialog_data)
    message = "New meal entry cancelled"
    await dialog_utils.no_markup_message(update, message)
    return await end_conversation(update, context)


async def end_conversation(update, context):
    # delete conversation data before ending new meal conversation
    meal_dialog_data = context.user_data.pop(DataKeys.MEAL_DATA)
    if MealDataEntry.PARENT_ID not in meal_dialog_data:
        return ConversationHandler.END

    parent_id = meal_dialog_data[MealDataEntry.PARENT_ID]
    if parent_id == ConversationID.DAY_VIEW:
        # note - if the current conversation is a parent of "meals dataview" conversation
        # the parent already haas the correct date data to display the correct view
        await meals_dataview_utils.message_day_meals(
            update, context, update_existing=False
        )
    elif parent_id == ConversationID.START_MENU:
        await start_menu_utils.send_existing_user_options(
            update, meal_dialog_data[MealDataEntry.USER]
        )
    else:
        logger.error(f"New meal dialog has unexpected parent value {parent_id}")


    return ConversationHandler.END


async def handle_edit_meal_inline_callback(update, context):
    await init_meal_dialog_data(update, context)

    await dialog_utils.handle_inline_keyboard_callback(
        update, delete_keyboard=True
    )
    data_str = update.callback_query.data
    data_value = InlineButtonDataKeyValue.from_str(data_str).value
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    meal_dialog_data[MealDataEntry.DATA_MODE] = MealDataMode.UPDATE

    try:
        meal_id = int(data_value)
    except (ValueError, TypeError) as e:
        logger.error(
            f"Cannot get meal_id for the meal to edit, value is {data_value}"
        )
        logger.error(e)
        return await end_conversation(update, context)

    with get_session() as session:
        existing_meal = select_meals.select_meal_eaten_by_meal_id(
            session, meal_id
        )
    if existing_meal is None:
        await dialog_utils.no_markup_message(update, "Meal data is missing")
        logger.error(f"Meal data for meal_id={meal_id} is missing")
        return await end_conversation(update, context)
    meal_dialog_data[MealDataEntry.MEAL_OBJECT] = existing_meal
    await new_meal_utils.ask_edit_mode(update)
    return NewMealStages.CHOOSE_EDIT_MODE


async def handle_choose_edit_mode(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    new_meal_utils.reset_ai_data(meal_dialog_data)
    input_mode = update.message.text

    if input_mode == EditMode.ADJUST_WITH_AI.value:
        meal = meal_dialog_data[MealDataEntry.MEAL_OBJECT]
        meal_dialog_data[MealDataEntry.LAST_AI_MESSAGE_LIST] = \
            openai_meal_chat.get_assistant_message_from_eaten_meal(meal)
        await new_meal_utils.ask_for_ai_edit_information(update)
        return NewMealStages.ADD_MORE_INFO_FOR_AI

    if input_mode == EditMode.MANUAL.value:
        pass
        # await new_meal_utils.ask_for_meal_description(update)
        # return NewMealStages.DESCRIBE_MEAL_MANUALLY

    if input_mode == EditMode.CHANGE_DATE_TIME.value:
        pass
        # await new_meal_utils.ask_for_meal_description(update)
        # return NewMealStages.DESCRIBE_MEAL_MANUALLY

    else:
        # assume input is a description for AI
        return await handle_assume_describe_for_ai(update, context)


async def handle_edit_info_for_ai(update, context):
    meal_dialog_data = context.user_data[DataKeys.MEAL_DATA]
    extra_info = update.message.text

    meal = meal_dialog_data[MealDataEntry.EXISTING_MEAL_OBJECT]
    prev_ai_messages = meal_dialog_data[MealDataEntry.LAST_AI_MESSAGE_LIST] = [
        openai_meal_chat.get_assistant_message_from_eaten_meal(meal)
    ]

    try:
        await dialog_utils.no_markup_message(update, "Sending request to AI...\nPlease wait")
        ai_response = openai_meal_chat.update_meal_estimate(
            prev_ai_messages, extra_info
        )
    except Exception as e:
        logger.error(f"handle_edit_info_for_ai exception: {e}" + "\n" + f"{traceback.format_exc()}")
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
