from telegram import ReplyKeyboardRemove
from telegram.ext import filters
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler
from enum import Enum
import dateparser
import timezonefinder
import pint
from chatbot.config import Commands, u_reg
from dateutil import tz
from database import update_mysql, common_mysql, select_mysql
from chatbot import new_user_misc
import logging
import re


timezone_finder = timezonefinder.TimezoneFinder(in_memory=True)


class NewUserStages(Enum):
    CONFIRM_NAME = 0
    NAME = 1
    GENDER = 2
    DATE_OF_BIRTH = 3
    TIMEZONE = 4
    HEIGHT = 5
    WEIGHT = 6
    # ACTIVITY_LEVEL
    GOAL = 7


class UpdateUserMode(Enum):
    NEW = 0
    UPDATE = 1


def get_new_user_conversation_handler():
    text_only_filter = filters.TEXT & ~filters.COMMAND
    entry_points = [
        CommandHandler(Commands.NEW_USER, on_new_user),
        CommandHandler(Commands.UPDATE_USER, on_update_user),
    ]
    states = {
        NewUserStages.CONFIRM_NAME: [MessageHandler(text_only_filter, on_confirm_name)],
        NewUserStages.NAME: [MessageHandler(text_only_filter, on_name)],
        NewUserStages.GENDER: [MessageHandler(text_only_filter, on_gender)],
        NewUserStages.DATE_OF_BIRTH: [MessageHandler(text_only_filter, on_date_of_birth)],
        NewUserStages.TIMEZONE: [MessageHandler(filters.LOCATION, on_timezone),
                                 MessageHandler(text_only_filter, on_timezone)],
        NewUserStages.HEIGHT: [MessageHandler(text_only_filter, on_height)],
        NewUserStages.WEIGHT: [MessageHandler(text_only_filter, on_weight)],
        NewUserStages.GOAL: [MessageHandler(text_only_filter, on_goal)]
    }
    for k in states.keys():
        states[k].extend(entry_points)

    fallbacks = [
        CommandHandler("cancel", on_cancel),
        # MessageHandler(filters.COMMAND, quiet_cancel)
    ]
    handler = ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=fallbacks,
    )
    return handler


async def on_update_user(update, context):
    context.user_data.clear()
    context.user_data["mode"] = UpdateUserMode.UPDATE

    tg_id = update.message.from_user.id

    with common_mysql.get_connection() as connection:
        existing_user_data = select_mysql.select_user_by_telegram_id(
            connection, tg_id
        )

    if existing_user_data is None:
        response = "User does not exists. "
        response += f"Use /{Commands.NEW_USER} instead"
        await update.message.reply_text(
            response, reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    dob = existing_user_data["DateOfBirth"]
    existing_user_data["DateOfBirth"] = dob.strftime('%d/%m/%Y')
    context.user_data["existing_user_data"] = existing_user_data

    context.user_data["name"] = existing_user_data["Name"]
    await update.message.reply_text(
        f"Hi {context.user_data['name']}! Let's update user data. \n" +
        "Is this your correct name?",
        reply_markup=new_user_misc.yes_no_markup(),
    )
    return NewUserStages.CONFIRM_NAME


async def on_new_user(update, context):
    context.user_data.clear()
    context.user_data["mode"] = UpdateUserMode.NEW

    tg_id = update.message.from_user.id

    with common_mysql.get_connection() as connection:
        existing_user_data = select_mysql.select_user_by_telegram_id(
            connection, tg_id
        )

    if existing_user_data is not None:
        response = "User exists. "
        if existing_user_data["IsActive"]:
            response += "User activated"
        else:
            response += "User awaits activation"
        response += f"\nUse /{Commands.UPDATE_USER} instead"
        await update.message.reply_text(
            response, reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    name = update.effective_user.first_name
    context.user_data["name"] = name
    await update.message.reply_text(
        f"Hi {context.user_data['name']}!  Let's set up a new user. \n" +
        "Is this your correct name?",
        reply_markup=new_user_misc.yes_no_markup(),
    )
    return NewUserStages.CONFIRM_NAME


async def on_confirm_name(update, context):
    confirm = update.message.text
    if confirm not in ("yes", "no"):
        await new_user_misc.wrong_value_message(update)
        await update.message.reply_text(
            "Is this your correct name?",
            reply_markup=new_user_misc.yes_no_markup()
        )
    confirmed = (confirm == "yes")

    if confirmed:
        await new_user_misc.gender_question(update)
        return NewUserStages.GENDER

    if updating_existing_user(context.user_data):
        tg_name = update.effective_user.first_name
        existing_name = context.user_data["existing_user_data"]["Name"]
        old_names = [tg_name, existing_name]
    else:
        old_names = []

    await new_user_misc.name_question(update, old_names)
    return NewUserStages.NAME


async def on_name(update, context):
    name = update.message.text

    if name == new_user_misc.new_value_query:
        await new_user_misc.name_question(update)
        return NewUserStages.NAME

    if len(name) == 0:
        await new_user_misc.wrong_value_message(update)
        return NewUserStages.NAME

    await new_user_misc.gender_question(update)
    return NewUserStages.GENDER


async def on_gender(update, context):
    gender = update.message.text
    if gender not in ("male", "female"):
        await new_user_misc.wrong_value_message(update)
        await new_user_misc.gender_question(update)
        return NewUserStages.GENDER

    context.user_data["is_male"] = gender == "male"

    if updating_existing_user(context.user_data):
        existing_date = context.user_data["existing_user_data"]["DateOfBirth"]
    else:
        existing_date = None

    await new_user_misc.date_of_birth_question(update, existing_date)
    return NewUserStages.DATE_OF_BIRTH


async def on_date_of_birth(update, context):
    date_of_birth_str = update.message.text

    if date_of_birth_str == new_user_misc.new_value_query:
        await new_user_misc.date_of_birth_question(update)
        return NewUserStages.DATE_OF_BIRTH

    datetime_dob = dateparser.parse(
        date_of_birth_str, settings={'DATE_ORDER': 'DMY'}
    )
    if datetime_dob is None:
        await new_user_misc.wrong_value_message(update)
        await new_user_misc.date_of_birth_question(update)
        return NewUserStages.DATE_OF_BIRTH

    dob_date = datetime_dob.date()
    context.user_data["date_of_birth"] = dob_date

    await update.message.reply_text(
        f"Your date of birth is {dob_date.strftime("%d-%B-%Y")}",
        reply_markup=ReplyKeyboardRemove()
    )

    if updating_existing_user(context.user_data):
        existing_tz = context.user_data["existing_user_data"]["TimeZone"]
    else:
        existing_tz = None

    await new_user_misc.timezone_question(update, existing_tz)
    return NewUserStages.TIMEZONE


async def on_timezone(update, context):
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
        context.user_data["time_zone"] = timezone_str
    else:
        await new_user_misc.wrong_value_message(update)
        return NewUserStages.TIMEZONE

    await update.message.reply_text(
        f"Your timezone is {timezone_str}",
        reply_markup=ReplyKeyboardRemove()
    )

    if updating_existing_user(context.user_data):
        old_height = (
            str(context.user_data["existing_user_data"]["Height"]) + " cm"
        )
    else:
        old_height = None

    await new_user_misc.height_question(update, old_height)
    return NewUserStages.HEIGHT


async def on_height(update, context):
    height_str = update.message.text

    if height_str == new_user_misc.new_value_query:
        await new_user_misc.height_question(update)
        return NewUserStages.HEIGHT

    height_cm = get_height_cm(height_str)

    if height_cm is None:
        await new_user_misc.wrong_value_message(update)
        await new_user_misc.height_question(update)
        return NewUserStages.HEIGHT

    context.user_data["height"] = height_cm

    if updating_existing_user(context.user_data):
        old_weight = (
            str(context.user_data["existing_user_data"]["Weight"]) + " kg"
        )
    else:
        old_weight = None

    await new_user_misc.weight_question(update, old_weight)
    return NewUserStages.WEIGHT


def get_height_cm(height_str):
    height_str = height_str.lower()

    feet_match = re.search(r"(\d+)'(\d+)?\"?", height_str)
    if feet_match:
        feet = feet_match.group(1)
        inches = feet_match.group(2) if feet_match.group(2) else "0"
        height_str = f"{feet} feet + {inches} inches "

    try:
        height_with_unit = u_reg(height_str)
    except pint.PintError:
        return None

    # deduce unit from the magnitude
    if not isinstance(height_with_unit, pint.Quantity):
        if height_with_unit < 3:
            height_with_unit = height_with_unit * u_reg("m")
        elif height_with_unit < 9:
            height_with_unit = height_with_unit * u_reg("ft")
        elif 90 < height_with_unit < 300:
            height_with_unit = height_with_unit * u_reg("cm")
        else:
            return None

    height_cm = height_with_unit.to("cm").magnitude
    good_height = 90 < height_cm < 300

    if good_height:
        return height_cm
    else:
        return None


async def on_weight(update, context):
    weight_str = update.message.text

    if weight_str == new_user_misc.new_value_query:
        await new_user_misc.weight_question(update)
        return NewUserStages.WEIGHT

    weight_kg = get_weight_kg(weight_str)

    if weight_kg is None:
        await new_user_misc.wrong_value_message(update)
        await new_user_misc.weight_question(update)
        return NewUserStages.WEIGHT

    context.user_data["weight"] = weight_kg

    await new_user_misc.goal_question(update)
    return NewUserStages.GOAL


def get_weight_kg(weight_str):
    weight_str = weight_str.lower()
    try:
        weight_with_unit = u_reg(weight_str)
        # assume units to be kilograms
        if not isinstance(weight_with_unit, pint.Quantity):
            weight_with_unit = weight_with_unit * u_reg("kg")
    except pint.PintError:
        return None

    weight_kg = weight_with_unit.to("kg").magnitude
    good_weight = 25 < weight_kg < 650

    if good_weight:
        return weight_kg
    else:
        return None


async def on_goal(update, context):
    goal = update.message.text
    if goal not in new_user_misc.goals:
        await new_user_misc.wrong_value_message(update)
        await new_user_misc.goal_question(update)
    context.user_data["goal"] = goal
    return await process_new_user_data(update, context)


async def process_new_user_data(update, context):
    user_data = context.user_data

    name = user_data["name"]
    gender = "male" if user_data["is_male"] else "female"
    date_of_birth = user_data["date_of_birth"]
    height = user_data["height"]
    weight = user_data["weight"]
    goal = user_data["goal"]
    time_zone = user_data["time_zone"]
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
            if updating_existing_user(context.user_data):
                update_mysql.update_user(
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
                update_mysql.create_new_user(
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

    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def on_cancel(update, context):
    if updating_existing_user(context.user_data):
        again_command = f"/{Commands.UPDATE_USER}"
    else:
        again_command = f"/{Commands.NEW_USER}"

    await update.message.reply_text(
        "Cancelled. " +
        f"Use {again_command} command to start again!",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def quiet_cancel(update, context):
    return ConversationHandler.END


def updating_existing_user(user_data):
    return user_data["mode"] == UpdateUserMode.UPDATE
