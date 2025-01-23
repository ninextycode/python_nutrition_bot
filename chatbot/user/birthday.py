import datetime
import logging
from telegram.ext import filters, MessageHandler
from chatbot import dialog_utils
from database import common_sql
from database.select import select_users
import calendar


logger = logging.getLogger(__name__)


def get_birthday_handler():
    text_or_command_filter = filters.TEXT
    return MessageHandler(text_or_command_filter, check_for_birthday)


async def send_birthday_message(update, user):
    dt_now = user.get_datetime_now()
    date_now = dt_now.date()
    bday_month = (user.date_of_birth.day, user.date_of_birth.month)

    # Handle February 29 for non-leap years
    if bday_month == (29, 2) and not calendar.isleap(date_now.year):
        dob_this_year = datetime.date(date_now.year, 2, 28)
    else:
        dob_this_year = datetime.date(
            date_now.year, bday_month[1], bday_month[0]
        )

    congrat_range_start = dob_this_year
    congrat_range_end = dob_this_year + datetime.timedelta(days=3)

    if (
        (congrat_range_start <= date_now <= congrat_range_end) and
        user.last_birthday_congratulated != date_now.year
    ):
        today_is_line = "Today is " + dt_now.strftime("%d %B %Y")
        if date_now != dob_this_year:
            days_from_bd = (date_now - dob_this_year).days
            if days_from_bd == 1:
                day_s = "day"
            else:
                day_s = "days"
            today_is_line = (
                today_is_line + "\n" +
                f"Just {days_from_bd} {day_s} from your birthday!"
            )

        await dialog_utils.keep_markup_message(
            update, (
                today_is_line + "\n\n" +
                "🎉 🥳 🎉 🥳 🎉\n\n" +
                f"Happy Birthday {user.name}!"
            )
        )
        return True
    else:
        return False


async def check_for_birthday(update, context):
    with common_sql.get_session() as session:
        user = select_users.select_user_by_telegram_id(
            session, update.message.from_user.id
        )
    if user is None:
        return

    birthday_message_sent = await send_birthday_message(update, user)
    if birthday_message_sent:
        user.last_birthday_congratulated = user.get_datetime_now().year

    try:
        with common_sql.get_session() as session:
            session.merge(user)
            session.commit()

    except Exception as e:
        logging.exception(e)
        await dialog_utils.no_markup_message(
            update, "Database user data update error"
        )