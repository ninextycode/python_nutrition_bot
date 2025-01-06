from telegram import ReplyKeyboardRemove
from telegram.ext import filters
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler
from enum import Enum, auto
import dateparser
import timezonefinder
from chatbot.config import Commands, registration_password
from dateutil import tz
from database import common_sql
from database.update import update_users
from database.select import select_users
from chatbot.user import user_utils
from chatbot.user.user_utils import (
    UserDataEntry, MaleFemaleOption,
    GoalOption, ActivityLevelOption, ConfirmTargetOption, TargetTypeOption
)
from chatbot.config import DataKeys
from database.food_database_model import (
    User, TimeZone, GoalSqlEntry, MaleFemaleSqlEntry, ActivityLevelSqlEntry, NutritionType, UserTarget
)
from chatbot import dialog_utils
import logging


timezone_finder = timezonefinder.TimezoneFinder(in_memory=True)


class NewUserStages(Enum):
    CHECK_REGISTRATION_PASSWORD = auto()
    CONFIRM_NAME = auto()
    NAME = auto()
    GENDER = auto()
    DATE_OF_BIRTH = auto()
    TIMEZONE = auto()
    HEIGHT = auto()
    WEIGHT = auto()
    ACTIVITY_LEVEL = auto()
    GOAL = auto()
    KETO = auto()
    CONFIRM_TARGET = auto()
    TARGET_VALUES_MANUAL_ENTRY = auto()
    TARGET_TYPE_MANUAL_ENTRY = auto()


def get_new_user_conversation_handler():
    text_only_filter = filters.TEXT & ~filters.COMMAND
    entry_points = [
        CommandHandler(Commands.NEW_USER.value, handle_new_user),
        CommandHandler(Commands.UPDATE_USER.value, handle_update_user),
    ]
    states = {
        NewUserStages.CHECK_REGISTRATION_PASSWORD: [MessageHandler(text_only_filter, check_reg_password)],
        NewUserStages.CONFIRM_NAME: [MessageHandler(text_only_filter, handle_confirm_name)],
        NewUserStages.NAME: [MessageHandler(text_only_filter, handle_name)],
        NewUserStages.GENDER: [MessageHandler(text_only_filter, handle_gender)],
        NewUserStages.DATE_OF_BIRTH: [MessageHandler(text_only_filter, handle_date_of_birth)],
        NewUserStages.TIMEZONE: [MessageHandler(filters.LOCATION, handle_timezone),
                                 MessageHandler(text_only_filter, handle_timezone)],
        NewUserStages.HEIGHT: [MessageHandler(text_only_filter, handle_height)],
        NewUserStages.WEIGHT: [MessageHandler(text_only_filter, handle_weight)],
        NewUserStages.ACTIVITY_LEVEL: [MessageHandler(text_only_filter, handle_activity_level)],
        NewUserStages.GOAL: [MessageHandler(text_only_filter, handle_goal)],
        NewUserStages.KETO: [MessageHandler(text_only_filter, handle_keto_choice)],
        NewUserStages.CONFIRM_TARGET: [
            MessageHandler(text_only_filter, handle_confirm_target)
        ],
        NewUserStages.TARGET_VALUES_MANUAL_ENTRY: [
            MessageHandler(text_only_filter, handle_target_values_manual_entry)
        ],
        NewUserStages.TARGET_TYPE_MANUAL_ENTRY: [
            MessageHandler(text_only_filter, handle_target_type_manual_entry)
        ],
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


async def handle_update_user(update, context):
    context.user_data[DataKeys.USER_DATA] = dict()
    user_data = context.user_data[DataKeys.USER_DATA]

    tg_id = update.message.from_user.id

    with common_sql.get_session() as session:
        old_user = select_users.select_user_by_telegram_id(
            session, tg_id
        )

    if old_user is None:
        await dialog_utils.user_does_not_exist_message(update)
        return ConversationHandler.END

    user_data[UserDataEntry.OLD_USER_OBJECT] = old_user
    user_data[UserDataEntry.NEW_USER_OBJECT] = User(
        telegram_id=update.message.from_user.id
    )

    await user_utils.ask_to_confirm_existing_name(update, old_user.name)
    return NewUserStages.CONFIRM_NAME


async def handle_new_user(update, context):
    context.user_data[DataKeys.USER_DATA] = dict()
    user_data = context.user_data[DataKeys.USER_DATA]

    tg_id = update.message.from_user.id

    with common_sql.get_session() as session:
        old_user = select_users.select_user_by_telegram_id(
            session, tg_id
        )

    if old_user is not None:
        response = "User exists. "
        if old_user.is_activated:
            response += "User activated"
        else:
            response += "User awaits activation"
        response += f"\nUse /{Commands.UPDATE_USER.value} instead"
        await update.message.reply_text(
            response, reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    user_data[UserDataEntry.NEW_USER_OBJECT] = User(
        telegram_id=update.message.from_user.id
    )

    await user_utils.ask_for_password(update)
    return NewUserStages.CHECK_REGISTRATION_PASSWORD


async def check_reg_password(update, context):
    new_user: User = context.user_data[DataKeys.USER_DATA][UserDataEntry.NEW_USER_OBJECT]
    user_password = update.message.text
    if user_password == registration_password:
        new_user.name = update.effective_user.first_name
        await user_utils.ask_to_confirm_existing_name(update, new_user.name)
        return NewUserStages.CONFIRM_NAME
    else:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_for_password(update)
        return NewUserStages.CHECK_REGISTRATION_PASSWORD


async def handle_confirm_name(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    old_user: User = user_data.get(UserDataEntry.OLD_USER_OBJECT, None)

    confirm = update.message.text
    if confirm not in dialog_utils.YesNo:
        await dialog_utils.wrong_value_message(update)
        await update.message.reply_text(
            "Is this your correct name?",
            reply_markup=dialog_utils.yes_no_markup()
        )
        return NewUserStages.CONFIRM_NAME
    confirmed = (confirm == dialog_utils.YesNo.YES.value)

    if confirmed:
        await user_utils.ask_gender_question(update)
        return NewUserStages.GENDER

    if old_user is not None:
        tg_name = update.effective_user.first_name
        existing_name = old_user.name
        old_names = {tg_name, existing_name}
    else:
        old_names = []

    await user_utils.ask_for_name(update, old_names)
    return NewUserStages.NAME


async def handle_name(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    name = update.message.text

    if name == user_utils.new_value_query:
        await user_utils.ask_for_name(update)
        return NewUserStages.NAME

    if len(name) == 0:
        await dialog_utils.wrong_value_message(update)
        return NewUserStages.NAME

    new_user.name = name

    await user_utils.ask_gender_question(update)
    return NewUserStages.GENDER


async def handle_gender(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    old_user: User = user_data.get(UserDataEntry.OLD_USER_OBJECT, None)

    gender = update.message.text
    if gender not in MaleFemaleOption:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_gender_question(update)
        return NewUserStages.GENDER

    new_user.gender_obj = MaleFemaleSqlEntry[MaleFemaleOption(gender).name].value

    if old_user is not None:
        existing_dob = old_user.date_of_birth
    else:
        existing_dob = None

    await user_utils.ask_date_of_birth_question(update, existing_dob)
    return NewUserStages.DATE_OF_BIRTH


async def handle_date_of_birth(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    old_user: User = user_data.get(UserDataEntry.OLD_USER_OBJECT, None)

    date_of_birth_str = update.message.text

    if date_of_birth_str == user_utils.new_value_query:
        await user_utils.ask_date_of_birth_question(update)
        return NewUserStages.DATE_OF_BIRTH

    datetime_dob = dateparser.parse(
        date_of_birth_str, settings={'DATE_ORDER': 'DMY'}
    )
    if datetime_dob is None:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_date_of_birth_question(update)
        return NewUserStages.DATE_OF_BIRTH

    dob_date = datetime_dob.date()
    new_user.date_of_birth = dob_date

    await dialog_utils.no_markup_message(
        update, f"Your date of birth is {dob_date.strftime('%d-%B-%Y')}"
    )

    if old_user is not None:
        existing_tz = old_user.timezone_obj.timezone
    else:
        existing_tz = None

    await user_utils.ask_timezone_question(update, existing_tz)
    return NewUserStages.TIMEZONE


async def handle_timezone(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    old_user: User = user_data.get(UserDataEntry.OLD_USER_OBJECT, None)
    user_location = update.message.location

    timezone_str = None

    if user_location is not None:
        try:
            timezone_str = timezone_finder.timezone_at(
                lng=user_location.longitude,
                lat=user_location.latitude
            )
        except ValueError:
            pass
    else:
        timezone_str = update.message.text

    if timezone_str is not None:
        timezone_obj = tz.gettz(timezone_str)
    else:
        timezone_obj = None

    if timezone_obj is not None:
        new_user.timezone_obj = TimeZone.get_if_exists_or_create_new(timezone=timezone_str)
    else:
        await dialog_utils.wrong_value_message(update)
        return NewUserStages.TIMEZONE

    await dialog_utils.no_markup_message(
        update, f"Your timezone is {timezone_str}"
    )

    if old_user is not None:
        old_height = str(old_user.height) + " cm"
    else:
        old_height = None

    await user_utils.ask_height_question(update, old_height)
    return NewUserStages.HEIGHT


async def handle_height(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    old_user: User = user_data.get(UserDataEntry.OLD_USER_OBJECT, None)
    height_str = update.message.text

    if height_str == user_utils.new_value_query:
        await user_utils.ask_height_question(update)
        return NewUserStages.HEIGHT

    height_cm = user_utils.get_height_cm(height_str)

    if height_cm is None:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_height_question(update)
        return NewUserStages.HEIGHT

    new_user.height = height_cm

    if old_user is not None:
        old_weight = str(old_user.weight) + " kg"
    else:
        old_weight = None

    await user_utils.ask_weight_question(update, old_weight)
    return NewUserStages.WEIGHT


async def handle_weight(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    weight_str = update.message.text

    if weight_str == user_utils.new_value_query:
        await user_utils.ask_weight_question(update)
        return NewUserStages.WEIGHT

    weight_kg = user_utils.get_weight_kg(weight_str)

    if weight_kg is None:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_weight_question(update)
        return NewUserStages.WEIGHT

    new_user.weight = weight_kg

    old_user: User = user_data.get(UserDataEntry.OLD_USER_OBJECT, None)
    if old_user is not None:
        new_user.goal_obj = old_user.goal_obj
        new_user.activity_level_obj = old_user.activity_level_obj
        new_user.user_target_obj = old_user.user_target_obj

        await user_utils.ask_to_confirm_target(
            update, new_user.user_target_obj
        )
        return NewUserStages.CONFIRM_TARGET
    else:
        await user_utils.ask_activity_level(update)
        return NewUserStages.ACTIVITY_LEVEL


async def handle_activity_level(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]

    activity_level = update.message.text
    if activity_level not in ActivityLevelOption:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_activity_level(update)

    try:
        new_user.activity_level_obj = ActivityLevelSqlEntry[ActivityLevelOption(activity_level).name].value
    except KeyError:
        await dialog_utils.wrong_value_message(
            update, f"Database entry for \"{activity_level}\" goal does not exist"
        )
        await user_utils.ask_activity_level(update)

    await user_utils.ask_goal_question(update)
    return NewUserStages.GOAL


async def handle_goal(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    goal = update.message.text
    if goal not in GoalOption:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_goal_question(update)

    try:
        new_user.goal_obj = GoalSqlEntry[GoalOption(goal).name].value
    except KeyError:
        await dialog_utils.wrong_value_message(
            update, f"Database entry for \"{goal}\" goal does not exist"
        )
        await user_utils.ask_goal_question(update)

    await user_utils.ask_if_keto(update)
    return NewUserStages.KETO


async def handle_keto_choice(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]

    is_keto_val = update.message.text
    if is_keto_val not in dialog_utils.YesNo:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_if_keto(update)
        return NewUserStages.KETO
    user_data[UserDataEntry.IS_KETO] = (is_keto_val == dialog_utils.YesNo.YES.value)
    user_utils.assign_target_obj(user_data)

    user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    await user_utils.ask_to_confirm_target(update, user.user_target_obj)
    return NewUserStages.CONFIRM_TARGET


async def handle_confirm_target(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    user: User = user_data[UserDataEntry.NEW_USER_OBJECT]

    confirm_response = update.message.text

    if confirm_response == ConfirmTargetOption.CONFIRM.value:
        await dialog_utils.no_markup_message(update, "Nutrition target confirmed")
        return await process_new_user_data(update, context)
    elif confirm_response == ConfirmTargetOption.CHOOSE_DIFFERENT.value:
        await user_utils.ask_activity_level(update)
        return NewUserStages.ACTIVITY_LEVEL
    elif confirm_response == ConfirmTargetOption.ENTER_MANUALLY.value:
        await user_utils.ask_to_enter_target_manually(update)
        return NewUserStages.TARGET_VALUES_MANUAL_ENTRY
    else:
        await user_utils.ask_to_confirm_target(update, user.user_target_obj)
        return NewUserStages.CONFIRM_TARGET


async def handle_target_values_manual_entry(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    nutrition_text = update.message.text

    nutrition_data = dialog_utils.parse_nutrition_message(
        nutrition_text, NutritionType.without_weight()
    )

    if nutrition_data is None:
        await dialog_utils.wrong_value_message(update, "Nutrition string parsing failed.")
        await user_utils.ask_to_enter_target_manually(update)
        return NewUserStages.TARGET_VALUES_MANUAL_ENTRY

    if user.user_target_obj is None:
        user.user_target_obj = UserTarget()

    user.user_target_obj.calories = nutrition_data[NutritionType.CALORIES]
    user.user_target_obj.protein = nutrition_data[NutritionType.PROTEIN]
    user.user_target_obj.fat = nutrition_data[NutritionType.FAT]
    user.user_target_obj.carbs = nutrition_data[NutritionType.CARBS]

    await user_utils.ask_target_type(update)
    return NewUserStages.TARGET_TYPE_MANUAL_ENTRY


async def handle_target_type_manual_entry(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    target_type_text = update.message.text

    if target_type_text == TargetTypeOption.MINIMUM.value:
        user.user_target_obj.target_type = "MINIMUM"
    elif target_type_text == TargetTypeOption.MAXIMUM.value:
        user.user_target_obj.target_type = "MAXIMUM"
    else:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_target_type(update)
        return NewUserStages.TARGET_TYPE_MANUAL_ENTRY

    user_data = context.user_data[DataKeys.USER_DATA]
    user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    await user_utils.ask_to_confirm_target(update, user.user_target_obj)
    return NewUserStages.CONFIRM_TARGET


async def process_new_user_data(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    old_user: User = user_data.get(UserDataEntry.OLD_USER_OBJECT, None)

    if old_user is None:
        await dialog_utils.no_markup_message(update, "Creating new user")
    else:
        await dialog_utils.no_markup_message(update, "Updating user")

    summary = (
        new_user.describe() + "\n\n" +
        new_user.user_target_obj.describe() + "\n\n" +
        "Account is approved automatically"
    )
    await dialog_utils.no_markup_message(update, summary)

    try:
        with common_sql.get_session() as session:
            if old_user is not None:
                new_user.id = old_user.id
                update_users.update_user(session, new_user)
            else:
                update_users.add_new_user(session, new_user)
        await dialog_utils.no_markup_message(update, "New data added")
    except Exception as e:
        logging.exception(e)
        await dialog_utils.no_markup_message(update, "Database error")

    return ConversationHandler.END


async def handle_cancel(update, context):
    user_data = context.user_data[DataKeys.USER_DATA]
    message = user_utils.get_message_on_cancel(user_data)

    command = update.message.text
    is_cancel_command = command.lower() in ["/cancel", "cancel"]
    if is_cancel_command:
        await dialog_utils.no_markup_message(update, message)
    else:
        await dialog_utils.keep_markup_message(
            update, message
        )
    return ConversationHandler.END
