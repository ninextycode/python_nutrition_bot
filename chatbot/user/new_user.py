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
    UserDataEntry, MaleFemaleOption, USER_DATA, GoalOption
)
from database.food_database_model import User, TimeZone, GoalEntry, MaleFemaleEntry
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
    # ACTIVITY_LEVEL
    GOAL = auto()


def get_new_user_conversation_handler():
    text_only_filter = filters.TEXT & ~filters.COMMAND
    entry_points = [
        CommandHandler(Commands.NEW_USER, handle_new_user),
        CommandHandler(Commands.UPDATE_USER, handle_update_user),
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
        NewUserStages.GOAL: [MessageHandler(text_only_filter, handle_goal)]
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
    context.user_data[USER_DATA] = dict()
    user_data = context.user_data[USER_DATA]

    tg_id = update.message.from_user.id

    with common_sql.get_session() as session:
        old_user = select_users.select_user_by_telegram_id(
            session, tg_id
        )

    if old_user is None:
        response = "User does not exists. "
        response += f"Use /{Commands.NEW_USER} instead"
        await update.message.reply_text(
            response, reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    user_data[UserDataEntry.OLD_USER_OBJECT] = old_user
    user_data[UserDataEntry.NEW_USER_OBJECT] = User(
        telegram_id=update.message.from_user.id
    )

    await user_utils.ask_to_confirm_existing_name(update, old_user.name)
    return NewUserStages.CONFIRM_NAME


async def handle_new_user(update, context):
    context.user_data[USER_DATA] = dict()
    user_data = context.user_data[USER_DATA]

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
        response += f"\nUse /{Commands.UPDATE_USER} instead"
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
    new_user: User = context.user_data[USER_DATA][UserDataEntry.NEW_USER_OBJECT]
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
    user_data = context.user_data[USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
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
    user_data = context.user_data[USER_DATA]
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
    user_data = context.user_data[USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    old_user: User = user_data.get(UserDataEntry.OLD_USER_OBJECT, None)

    gender = update.message.text
    if gender not in MaleFemaleOption:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_gender_question(update)
        return NewUserStages.GENDER

    new_user.gender_obj = MaleFemaleEntry[MaleFemaleOption(gender).name].value

    if old_user is not None:
        existing_dob = old_user.date_of_birth
    else:
        existing_dob = None

    await user_utils.ask_date_of_birth_question(update, existing_dob)
    return NewUserStages.DATE_OF_BIRTH


async def handle_date_of_birth(update, context):
    user_data = context.user_data[USER_DATA]
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
        update, f"Your date of birth is {dob_date.strftime("%d-%B-%Y")}"
    )

    if old_user is not None:
        existing_tz = old_user.timezone_obj.timezone
    else:
        existing_tz = None

    await user_utils.ask_timezone_question(update, existing_tz)
    return NewUserStages.TIMEZONE


async def handle_timezone(update, context):
    user_data = context.user_data[USER_DATA]
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
        except Exception:
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
    user_data = context.user_data[USER_DATA]
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
    user_data = context.user_data[USER_DATA]
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

    await user_utils.ask_goal_question(update)
    return NewUserStages.GOAL


async def handle_goal(update, context):
    user_data = context.user_data[USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    goal = update.message.text
    if goal not in GoalOption:
        await dialog_utils.wrong_value_message(update)
        await user_utils.ask_goal_question(update)

    try:
        new_user.goal_obj = GoalEntry[GoalOption(goal).name].value
    except KeyError:
        await dialog_utils.wrong_value_message(
            update, f"Database entry for \"{goal}\" goal does not exist"
        )
        await user_utils.ask_goal_question(update)

    return await process_new_user_data(update, context)


async def process_new_user_data(update, context):
    user_data = context.user_data[USER_DATA]
    new_user: User = user_data[UserDataEntry.NEW_USER_OBJECT]
    old_user: User = user_data.get(UserDataEntry.OLD_USER_OBJECT, None)

    if old_user is None:
        await dialog_utils.no_markup_message(update, "Creating new user")
    else:
        await dialog_utils.no_markup_message(update, "Updating user")

    summary = (
        new_user.describe() + "\n"
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
    user_data = context.user_data[USER_DATA]
    await user_utils.send_message_on_cancel(update, user_data)
    return ConversationHandler.END
