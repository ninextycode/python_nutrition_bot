from database.food_database_model import *
from database.select.select_users import select_user_by_telegram_id

def add_new_user(session, user):
    session.add(user)
    session.commit()


def update_user(session, user):
    if user.id is None:
        raise ValueError("User ID is None, cannot update")

    object_exists = session.scalar(sa.select(True).where(User.id == user.id))
    if object_exists is None:
        raise ValueError("User to be updated does not exist")

    # it appears that when sqlalchemy ORM object is created
    # without explicitly setting its field/column values,
    # the unspecified values do not exist in the object (not even as "None" placeholders)
    # and so session.merge won't update them
    #
    # It's possible to use partially constructed object in merge function to
    # make an update to only a subset of values, leaving other values intact
    updated_user = session.merge(user)
    session.commit()
    return updated_user


def activate_user(session, user_id):
    user = session.scalar(sa.select(User).where(User.id == user_id))
    user.is_activated = True
    session.commit()


def deactivate_user(session, user_id):
    user = session.scalar(sa.select(User).where(User.id == user_id))
    user.is_activated = False
    session.commit()


def delete_user(session, user_value):
    if isinstance(user_value, User):
        session.delete(user_value)
    else:
        sql = sa.delete(User).where(User.id == user_value)
        session.execute(sql)
    session.commit()


def delete_user_by_telegram_id(session, tg_id):
    user = select_user_by_telegram_id(session, tg_id)
    if user is None:
        return False

    delete_user(session, user)
    session.commit()
    return True
