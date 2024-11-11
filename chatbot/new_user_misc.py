from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
import datetime


new_value_query = "Enter new value"
goals = [
    "lose weight",
    "lose weight slowly",
    "maintain weight",
    "gain muscle slowly",
    "gain muscle",
]


async def ask_question(update, question, old_answers=None):
    if old_answers is not None:
        reply_markup = old_value_or_enter_new_markup(old_answers)
    else:
        reply_markup = ReplyKeyboardRemove()

    await update.message.reply_text(
        question, reply_markup=reply_markup
    )


def old_value_or_enter_new_markup(old_values=None):
    if old_values is None:
        old_values = []

    if not isinstance(old_values, (list, tuple)):
        old_values = [old_values]

    old_values = list(set(old_values))

    layout = [[f"{v}"] for v in old_values]
    layout.append([new_value_query])
    return ReplyKeyboardMarkup(
        layout, resize_keyboard=True
    )


def yes_no_markup():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("yes"), KeyboardButton("no")]],
        resize_keyboard=True
    )


async def date_of_birth_question(update, old_date=None):
    if old_date is not None and isinstance(old_date, datetime.date):
        old_date = old_date.strftime("%d/%m/%Y")
    question = (
        "What is your date of birth? \n"
        "(Day/Month/Year)"
    )
    await ask_question(
        update, question, old_date
    )


async def name_question(update, old_names=None):
    await ask_question(
        update, "Please enter your name", old_names
    )


async def gender_question(update):
    await update.message.reply_text(
        "Please select your gender",
        reply_markup=male_female_markup()
    )


def male_female_markup():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("male"), KeyboardButton("female")]],
        resize_keyboard=True
    )


async def height_question(update, old_height=None):
    await ask_question(
        update, "What is your height?", old_height
    )


async def weight_question(update, old_weight=None):
    await ask_question(
        update, "What is your weight? (kg unit assumed)", old_weight
    )


async def goal_question(update):
    await update.message.reply_text(
        "What is your goal?",
        reply_markup=goal_markup()
    )


def goal_markup():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(g)]
            for g in goals
        ],
        resize_keyboard=True
    )


async def timezone_question(update, old_timezone=None):
    await update.message.reply_text(
        "Let's determine your timezone",
        reply_markup=location_markup(old_timezone)
    )


def location_markup(existing_values=None):
    keyboard_layout = [
        [KeyboardButton("Send location", request_location=True)]
    ]

    if existing_values is None:
        existing_values = []

    if not isinstance(existing_values, (list, tuple)):
        existing_values = [existing_values]

    if existing_values is not None:
        keyboard_layout.extend([[v] for v in existing_values])

    return ReplyKeyboardMarkup(
        keyboard_layout,
        resize_keyboard=True
    )
