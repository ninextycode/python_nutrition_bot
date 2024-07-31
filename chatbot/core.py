from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from chatbot.config import secret

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')


def run_bot():
    app = ApplicationBuilder().token(secret).build()

    app.add_handler(CommandHandler("hello", hello))

    app.run_polling()



CREATE TABLE Persons (PersonID int, LastName varchar(255), FirstName varchar(255), Address varchar(255));