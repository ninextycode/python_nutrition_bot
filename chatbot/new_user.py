from telegram import ForceReply, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import filters
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler
from enum import Enum
import dateparser
import timezonefinder
import pint

from pint import UnitRegistry, PintError
import pint

NEW_USER_COMMAND = "new_user"
u_reg = pint.UnitRegistry()
timezone_finder = timezonefinder.TimezoneFinder(in_memory=True)
goals = [
    "lose weight",
    "lose weight slowly",
    "maintain weight",
    "gain muscle slowly",
    "gain muscle",
]

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


def get_new_user_conversation_handler():
    text_only_filter = filters.TEXT & ~filters.COMMAND
    handler = ConversationHandler(
        entry_points=[CommandHandler("new_user", on_new_user)],
        states={
            NewUserStages.CONFIRM_NAME: [MessageHandler(text_only_filter, on_confirm_name)],
            NewUserStages.NAME: [MessageHandler(text_only_filter, on_name)],
            NewUserStages.GENDER: [MessageHandler(text_only_filter, on_gender)],
            NewUserStages.DATE_OF_BIRTH: [MessageHandler(text_only_filter, on_date_of_birth)],
            NewUserStages.TIMEZONE: [MessageHandler(filters.LOCATION, on_timezone),
                                     MessageHandler(text_only_filter, on_timezone)],
            NewUserStages.HEIGHT: [MessageHandler(text_only_filter, on_height)],
            NewUserStages.WEIGHT: [MessageHandler(text_only_filter, on_weight)],
            NewUserStages.GOAL: [MessageHandler(text_only_filter, on_goal)]
        },
        fallbacks=[CommandHandler("cancel", on_cancel)],
    )
    return handler


async def on_new_user(update, context):
    name = update.effective_user.first_name
    context.user_data["name"] = name
    await update.message.reply_text(
        f"Hi {name}!  Let's set up a new user. \n" +
        "Is this your correct name?",
        reply_markup=yes_no_markup(),
    )
    return NewUserStages.CONFIRM_NAME


def yes_no_markup():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("yes"), KeyboardButton("no")]],
        resize_keyboard=True
    )


async def on_confirm_name(update, context):
    confirm = update.message.text
    if confirm not in ("yes", "no"):
        await update.message.reply_text(
            "Wrong value",
            reply_markup=yes_no_markup()
        )
    confirmed = (confirm == "yes")
    if confirmed:
        await update.message.reply_text(
            "Please select your gender",
            reply_markup=male_female_markup()
        )
        return NewUserStages.GENDER
    else:
        await update.message.reply_text(
            "Please enter your name",
            reply_markup=ReplyKeyboardRemove()
        )
        return NewUserStages.NAME


async def on_name(update, context):
    name = update.message.text
    if len(name) == 0:
        await update.message.reply_text(
            "Wrong value"
        )
        return NewUserStages.NAME
    else:
        await update.message.reply_text(
            "Please select your gender",
            reply_markup=male_female_markup()
        )
        return NewUserStages.GENDER


async def on_gender(update, context):
    gender = update.message.text
    if gender not in ("male", "female"):
        await update.message.reply_text(
            "Wrong value",
            reply_markup=male_female_markup()
        )
        return NewUserStages.GENDER

    context.user_data["is_male"] = gender == "male"
    await update.message.reply_text(
        "What is your date of birth? \n" +
        "(DD/MM/YYYY)",
        reply_markup=ReplyKeyboardRemove()
    )
    return NewUserStages.DATE_OF_BIRTH


def male_female_markup():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("male"), KeyboardButton("female")]],
        resize_keyboard=True
    )


async def on_date_of_birth(update, context):
    date_of_birth = update.message.text
    datetime_dob = dateparser.parse(date_of_birth, settings={'DATE_ORDER': 'DMY'})
    if datetime_dob is None:
        await update.message.reply_text(
            "Wrong value. Enter your date of birth"
        )
        return NewUserStages.DATE_OF_BIRTH

    context.user_data["date_of_birth"] = datetime_dob.date()

    await update.message.reply_text(
        "Let's determine your timezone", reply_markup=location_markup()
    )
    return NewUserStages.TIMEZONE


def location_markup():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Send location", request_location=True)]],
        resize_keyboard=True
    )


async def on_timezone(update, context):
    user_location = update.message.location
    request_location_again = False
    if user_location is None:
        request_location_again = True

    timezone = None
    if not request_location_again:
        try:
            timezone = timezone_finder.timezone_at(lng=user_location.longitude, lat=user_location.latitude)
        except Exception as e:
            request_location_again = True

    if request_location_again:
        await update.message.reply_text(
            "Problem with location data, try again", reply_markup=location_markup()
        )
        return NewUserStages.TIMEZONE

    await update.message.reply_text(f"Your timezone is {timezone}", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text("What is your height?")
    return NewUserStages.HEIGHT


async def on_height(update, context):
    height_str = update.message.text
    height_cm = get_height_cm(height_str)

    if height_cm is None:
        await update.message.reply_text("Wrong value. Enter your height:")
        return NewUserStages.HEIGHT

    context.user_data["height"] = height_cm
    await update.message.reply_text(
        "What is your weight? \n" +
        "If unit is unspecified, kg assumed"
    )
    return NewUserStages.WEIGHT


def get_height_cm(height_str):
    height_str = height_str.lower()
    try:
        height_with_unit = u_reg(height_str)
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
    except pint.PintError:
        return None

    height_cm = height_with_unit.to("cm").magnitude
    good_height = 90 < height_cm < 300

    if good_height:
        return height_cm
    else:
        return None


async def on_weight(update, context):
    weight = update.message.text
    weight_kg = get_weight_kg(weight)

    if weight_kg is None:
        await update.message.reply_text("Wrong value. Enter your weight:")
        return NewUserStages.WEIGHT

    context.user_data["weight"] = weight_kg
    await update.message.reply_text("What is your goal?", reply_markup=goal_markup())
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
    if goal not in goals:
        await update.message.reply_text(
            "Wrong value. Select your goal", reply_markup=goal_markup()
        )
    context.user_data["goal"] = goal
    return await process_new_user_data(update, context)


def goal_markup():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(g)]
            for g in goals
        ],
        resize_keyboard=True
    )


async def process_new_user_data(update, context):
    user_data = context.user_data

    name = user_data["name"]
    gender = "male" if user_data["is_male"] else "female"
    date_of_birth = user_data["date_of_birth"].strftime("%d/%m/%Y")
    height = f"{int(round(user_data["height"]))} cm"
    weight = f"{round(user_data["weight"], 1)} kg"
    goal = user_data["goal"]

    summary = (
        "New User Data:\n"
        f" - name: {name}\n"
        f" - gender: {gender}\n"
        f" - date_of_birth: {date_of_birth}\n"
        f" - height: {height}\n"
        f" - weight: {weight}\n"
        f" - goal: {goal}"
    )


    await update.message.reply_text(summary, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def on_cancel(update, context):
    await update.message.reply_text(
        "New user registration cancelled. \n" +
        "Use /new_user command to start again!"
    )
    return ConversationHandler.END

