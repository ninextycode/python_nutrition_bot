from database.food_database_model import User
import sqlalchemy as sa


def select_users(session) -> list[User]:
    users = session.scalars(sa.select(User)).fetchall()
    return users


def select_user_by_user_id(session, user_id) -> User:
    return session.scalar(sa.select(User).where(User.id == user_id))


def select_user_by_telegram_id(session, tg_id) -> User:
    return session.scalar(sa.select(User).where(User.telegram_id == tg_id))

