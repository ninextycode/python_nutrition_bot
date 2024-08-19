from database import select_mysql, common_mysql
from telegram import ReplyKeyboardRemove
from chatbot.config import Commands


async def get_existing_user_data(update, context):
    tg_id = update.message.from_user.id

    with common_mysql.get_connection() as connection:
        data = select_mysql.select_user_by_telegram_id(
            connection, tg_id
        )

    if data is None:
        await update.message.reply_text(
            f"User is missing. Use /{Commands.NEW_USER} command.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    message = "\n".join((
        "User data:",
        f" - Registration date : {data['CreatedUTCDateTime'].strftime('%d/%m/%Y')}",
        f" - TelegramID : {data['TelegramID']}",
        f" - Name : {data['Name']}",
        f" - Gender : {data['Gender']}",
        f" - IsActive : {data['IsActive']}",
        f" - Weight : {data['Weight']} kg",
        f" - Height : {data['Height']} cm",
        f" - Date of birth : {data['DateOfBirth'].strftime('%d/%m/%Y')}",
        f" - TimeZone : {data['TimeZone']}",
        f" - Goal : {data['Goal']}",
    ))
    await update.message.reply_text(
        message, reply_markup=ReplyKeyboardRemove()
    )
    return


async def delete_user(update, context):
    # todo only for testing
    tg_id = str(update.message.from_user.id)
    query = "DELETE FROM users WHERE TelegramID = %s ;"
    try:
        with common_mysql.get_connection() as connection:
            common_mysql.execute_query(connection, query, [tg_id])
            connection.commit()

        await update.message.reply_text(
            f"User deleted",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception:
        await update.message.reply_text(
            f"Database error",
            reply_markup=ReplyKeyboardRemove()
        )