from database.food_database_model.food_database_objects import *
import pytz


def get_user_timezone(session, user):
    if not isinstance(user, User):
        user_id = user
        user = session.scalar(sa.select(User).where(User.id == user_id))
        if user is None:
            raise ValueError(f"User with user_id={user_id} not found")
    return pytz.timezone(user.timezone_obj.timezone)


def convert_to_user_tz(session, user, *times):
    if len(times) == 0:
        return
    tz = get_user_timezone(session, user)

    times_list = list(times)
    # if tzinfo is None, assume UTC instead of local (default)
    for i, t in enumerate(times):
        if t.tzinfo is None:
            times_list[i] = t.replace(tzinfo=pytz.UTC)
    out_list = [t.astimezone(tz) for t in times_list]

    return out_list[0] if len(out_list) == 1 else out_list


def localize_to_user_tz(session, user, *times):
    if len(times) == 0:
        return
    tz = get_user_timezone(session, user)
    out_list = [tz.localize(t) for t in times]
    return out_list[0] if len(out_list) == 1 else out_list


def get_local_datetime_now(session, user):
    return convert_to_user_tz(
        session, user, datetime.datetime.now(datetime.UTC)
    )
