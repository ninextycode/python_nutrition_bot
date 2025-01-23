from enum import Enum, auto
from chatbot.config import DataKeys
from chatbot.dialog_utils import TextEnum


# used to handle child conversation endings in patent conversations
class ChildEndStage(Enum):
    NEW_MEAL_END = auto()
    MEALS_EATEN_VIEW_END = auto()


# inline keys can be used to start_menu parent conversations
# these ID values can be used to connect parent and child
class ConversationID(TextEnum):
    START_MENU = auto()
    DAY_VIEW = auto()
    SINGLE_MEAL_VIEW = auto()
    USER_DATA = auto()
    NUTRITION = auto()
    NEW_MEAL = auto()


def set_parent_data(context, parent_id, child_id, data):
    user_data = context.user_data
    if DataKeys.PARENT_DATA not in user_data:
        user_data[DataKeys.PARENT_DATA] = {}
    parent_data_dict = user_data[DataKeys.PARENT_DATA]
    if parent_id not in parent_data_dict:
        parent_data_dict[parent_id] = {}
    parent_data_dict[parent_id][child_id] = data


def pop_parent_data(context, parent_id, child_id):
    user_data = context.user_data
    if DataKeys.PARENT_DATA not in user_data:
        return None
    parent_data_dict = user_data[DataKeys.PARENT_DATA]
    if parent_id not in parent_data_dict:
        return None
    data_for_child = parent_data_dict[parent_id].pop(child_id, None)
    if len(parent_data_dict[parent_id]) == 0:
        parent_data_dict.pop(parent_id)
    return data_for_child
