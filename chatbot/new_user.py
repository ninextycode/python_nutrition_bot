from telegram import ReplyKeyboardRemove
from telegram.ext import filters
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler
from enum import Enum, auto
import dateparser
import timezonefinder
from chatbot.config import Commands, registration_password
from dateutil import tz
from database import common_mysql
from database.update import update_users
from database.select import select_users
from chatbot import new_user_utils
from chatbot.new_user_utils import (
    UserDataEntry, MaleFemale, USER_DATA, UpdateUserMode, updating_existing_user
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
    user_data[UserDataEntry.MODE] = UpdateUserMode.UPDATE

    tg_id = update.message.from_user.id

    with common_mysql.get_connection() as connection:
        # TODO need to convert to use the same keys as UserDataEntry
        old_user_data = select_users.select_user_by_telegram_id(
            connection, tg_id
        )

    if old_user_data is None:
        response = "User does not exists. "
        response += f"Use /{Commands.NEW_USER} instead"
        await update.message.reply_text(
            response, reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    dob = old_user_data[UserDataEntry.DATE_OF_BIRTH]
    old_user_data[UserDataEntry.DATE_OF_BIRTH] = dob.strftime('%d/%m/%Y')
    user_data[UserDataEntry.OLD_USER_DATA] = old_user_data

    user_data[UserDataEntry.NAME] = old_user_data[UserDataEntry.NAME]
    await new_user_utils.ask_to_confirm_existing_name(update, user_data)
    return NewUserStages.CONFIRM_NAME


async def handle_new_user(update, context):
    context.user_data[USER_DATA] = dict()
    user_data = context.user_data[USER_DATA]
    user_data[UserDataEntry.MODE] = UpdateUserMode.NEW

    tg_id = update.message.from_user.id

    with common_mysql.get_connection() as connection:
        old_user_data = select_users.select_user_by_telegram_id(
            connection, tg_id
        )

    if old_user_data is not None:
        response = "User exists. "
        if old_user_data[UserDataEntry.IS_ACTIVE]:
            response += "User activated"
        else:
            response += "User awaits activation"
        response += f"\nUse /{Commands.UPDATE_USER} instead"
        await update.message.reply_text(
            response, reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    await new_user_utils.ask_for_password(update)
    return NewUserStages.CHECK_REGISTRATION_PASSWORD


async def check_reg_password(update, context):
    user_data = context.user_data[USER_DATA]
    user_password = update.message.text
    if user_password == registration_password:
        user_data[UserDataEntry.NAME] = update.effective_user.first_name
        await new_user_utils.ask_to_confirm_existing_name(update, user_data)
        return NewUserStages.CONFIRM_NAME
    else:
        await dialog_utils.wrong_value_message(update)
        await new_user_utils.ask_for_password(update)
        return NewUserStages.CHECK_REGISTRATION_PASSWORD


async def handle_confirm_name(update, context):
    user_data = context.user_data[USER_DATA]
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
        await new_user_utils.ask_gender_question(update)
        return NewUserStages.GENDER

    if updating_existing_user(user_data):
        tg_name = update.effective_user.first_name
        existing_name = user_data[UserDataEntry.OLD_USER_DATA][UserDataEntry.NAME]
        old_names = [tg_name, existing_name]
    else:
        old_names = []

    await new_user_utils.ask_for_name(update, old_names)
    return NewUserStages.NAME


async def handle_name(update, context):
    name = update.message.text

    if name == new_user_utils.new_value_query:
        await new_user_utils.ask_for_name(update)
        return NewUserStages.NAME

    if len(name) == 0:
        await dialog_utils.wrong_value_message(update)
        return NewUserStages.NAME

    await new_user_utils.ask_gender_question(update)
    return NewUserStages.GENDER


async def handle_gender(update, context):
    user_data = context.user_data[USER_DATA]
    gender = update.message.text
    if gender not in new_user_utils.MaleFemale:
        await dialog_utils.wrong_value_message(update)
        await new_user_utils.ask_gender_question(update)
        return NewUserStages.GENDER

    user_data[UserDataEntry.IS_MALE] = (gender == new_user_utils.MaleFemale.MALE.value)

    if updating_existing_user(user_data):
        existing_date = user_data[UserDataEntry.OLD_USER_DATA][UserDataEntry.DATE_OF_BIRTH]
    else:
        existing_date = None

    await new_user_utils.ask_date_of_birth_question(update, existing_date)
    return NewUserStages.DATE_OF_BIRTH


async def handle_date_of_birth(update, context):
    user_data = context.user_data[USER_DATA]
    date_of_birth_str = update.message.text

    if date_of_birth_str == new_user_utils.new_value_query:
        await new_user_utils.ask_date_of_birth_question(update)
        return NewUserStages.DATE_OF_BIRTH

    datetime_dob = dateparser.parse(
        date_of_birth_str, settings={'DATE_ORDER': 'DMY'}
    )
    if datetime_dob is None:
        await dialog_utils.wrong_value_message(update)
        await new_user_utils.ask_date_of_birth_question(update)
        return NewUserStages.DATE_OF_BIRTH

    dob_date = datetime_dob.date()
    user_data[UserDataEntry.DATE_OF_BIRTH] = dob_date

    await dialog_utils.no_markup_message(
        update, f"Your date of birth is {dob_date.strftime("%d-%B-%Y")}"
    )

    if updating_existing_user(user_data):
        existing_tz = user_data[UserDataEntry.OLD_USER_DATA][UserDataEntry.TIME_ZONE]
    else:
        existing_tz = None

    await new_user_utils.ask_timezone_question(update, existing_tz)
    return NewUserStages.TIMEZONE


async def handle_timezone(update, context):
    user_data = context.user_data[USER_DATA]
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
        user_data[UserDataEntry.TIME_ZONE] = timezone_str
    else:
        await dialog_utils.wrong_value_message(update)
        return NewUserStages.TIMEZONE

    await dialog_utils.no_markup_message(
        update, f"Your timezone is {timezone_str}"
    )

    if updating_existing_user(user_data):
        old_height = (
            str(user_data[UserDataEntry.OLD_USER_DATA][UserDataEntry.HEIGHT]) + " cm"
        )
    else:
        old_height = None

    await new_user_utils.ask_height_question(update, old_height)
    return NewUserStages.HEIGHT


async def handle_height(update, context):
    user_data = context.user_data[USER_DATA]
    height_str = update.message.text

    if height_str == new_user_utils.new_value_query:
        await new_user_utils.ask_height_question(update)
        return NewUserStages.HEIGHT

    height_cm = new_user_utils.get_height_cm(height_str)

    if height_cm is None:
        await dialog_utils.wrong_value_message(update)
        await new_user_utils.ask_height_question(update)
        return NewUserStages.HEIGHT

    user_data[UserDataEntry.HEIGHT] = height_cm

    if updating_existing_user(user_data):
        old_weight = (
            str(user_data[UserDataEntry.OLD_USER_DATA][UserDataEntry.WEIGHT]) + " kg"
        )
    else:
        old_weight = None

    await new_user_utils.ask_weight_question(update, old_weight)
    return NewUserStages.WEIGHT


async def handle_weight(update, context):
    user_data = context.user_data[USER_DATA]
    weight_str = update.message.text

    if weight_str == new_user_utils.new_value_query:
        await new_user_utils.ask_weight_question(update)
        return NewUserStages.WEIGHT

    weight_kg = new_user_utils.get_weight_kg(weight_str)

    if weight_kg is None:
        await dialog_utils.wrong_value_message(update)
        await new_user_utils.ask_weight_question(update)
        return NewUserStages.WEIGHT

    user_data[UserDataEntry.WEIGHT] = weight_kg

    await new_user_utils.ask_goal_question(update)
    return NewUserStages.GOAL


async def handle_goal(update, context):
    user_data = context.user_data[USER_DATA]
    goal = update.message.text
    if goal not in new_user_utils.goals:
        await dialog_utils.wrong_value_message(update)
        await new_user_utils.ask_goal_question(update)
    user_data[UserDataEntry.GOAL] = goal
    return await process_new_user_data(update, context)


async def process_new_user_data(update, context):
    user_data = context.user_data[USER_DATA]

    # TODO this can only be simplified if I create a class for sql schema
    name = user_data[UserDataEntry.NAME]
    if user_data[UserDataEntry.IS_MALE]:
        gender = MaleFemale.MALE
    else:
        gender = MaleFemale.FEMALE
    date_of_birth = user_data[UserDataEntry.DATE_OF_BIRTH]
    height = user_data[UserDataEntry.HEIGHT]
    weight = user_data[UserDataEntry.WEIGHT]
    goal = user_data[UserDataEntry.GOAL]
    time_zone = user_data[UserDataEntry.TIME_ZONE]
    tg_id = update.message.from_user.id

    summary = (
        "User Data:\n"
        f" - name: {name}\n"
        f" - gender: {gender}\n"
        f" - date_of_birth: {date_of_birth.strftime('%d/%m/%Y')}\n"
        f" - height: {int(round(height))} cm\n"
        f" - weight: {round(weight)} kg\n"
        f" - goal: {goal}\n"
        f" - goal: {time_zone}\n"
        f" - unique telegram id: {tg_id}\n"
        "wait for your account to be approved"
    )

    try:
        with common_mysql.get_connection() as connection:
            if updating_existing_user(user_data):
                update_users.update_user(
                    connection=connection,
                    tg_id=tg_id,
                    name=name,
                    gender=gender,
                    goal=goal,
                    weight=weight,
                    height=height,
                    date_of_birth=date_of_birth,
                    time_zone=time_zone
                )
            else:
                update_users.create_new_user(
                    connection=connection,
                    name=name,
                    gender=gender,
                    goal=goal,
                    weight=weight,
                    height=height,
                    date_of_birth=date_of_birth,
                    tg_id=tg_id,
                    time_zone=time_zone
                )
        message = summary
    except Exception as e:
        logging.exception(e)
        message = "Database error"

    await dialog_utils.no_markup_message(update, message)
    return ConversationHandler.END


async def handle_cancel(update, context):
    user_data = context.user_data[USER_DATA]
    await new_user_utils.send_message_on_cancel(update, user_data)
    return ConversationHandler.END
