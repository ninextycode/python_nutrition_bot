from enum import Enum, auto
from chatbot.dialog_utils import is_collection
import numbers
from telegram import (
    InlineKeyboardMarkup, InlineKeyboardButton
)
from chatbot.dialog_utils import TextEnum
import json


class InlineButtonDataKeyValue:
    def __init__(self, key, value=None):
        self.key = key.value if isinstance(key, Enum) else key
        self.value = value


    @staticmethod
    def from_str(s: str):
        if " " in s:
            key, value = s.split(" ", 1)
        else:
            key, value = s, None
        if value is not None:
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        return InlineButtonDataKeyValue(key, value)

    def to_str(self):
        if self.value is None:
            key_value = self.key
        else:
            if isinstance(self.value, dict):
                value_s = json.dumps(self.value)
            else:
                value_s = str(self.value)
            key_value = self.key + " " + value_s
        n_bytes = len(key_value.encode("utf-8"))
        if n_bytes > 64:
            raise ValueError(
                key_value +
                f"\ncallback data size is larger than 64 bytes ({n_bytes})"
            )

        return key_value


class InlineButtonDataKey(TextEnum):
    def __call__(self, value=None):
        return self.add_value(value).to_str()

    def add_value(self, value=None):
        return InlineButtonDataKeyValue(self, value)

    def to_str(self, value=None):
        return self.add_value(value).to_str()


class StartConversationDataKey(InlineButtonDataKey):
    NEW_USER = auto()
    UPDATE_USER = auto()
    NEW_MEAL = auto()
    EDIT_MEAL = auto()
    VIEW_EATEN_MEALS = auto()
    VIEW_SAVED_MEALS = auto()
    NUTRITION = auto()


class InlineButtonDataValueGroup(TextEnum):
    @staticmethod
    def class_key():
        raise NotImplementedError()

    def to_key_value(self):
        return InlineButtonDataKeyValue(
            self.__class__.class_key(), self.value
        )

    def to_key_value_str(self):
        return self.to_key_value().to_str()


def inline_keys_markup(text_values, callback_data, n_btn_in_row=None):
    # single button layout
    if not is_collection(text_values):
        text_values = [text_values]
    if not is_collection(callback_data):
        callback_data = [callback_data]

    if len(text_values) != len(callback_data):
        raise ValueError("text_values and callback_data length do not match")

    if n_btn_in_row is None:
        n_btn_in_row = [len(text_values)]
    if isinstance(n_btn_in_row, numbers.Integral):
        n_btn_in_row = [n_btn_in_row]

    buttons = []
    for (t, d) in zip(text_values, callback_data):
        buttons.append(InlineKeyboardButton(t, callback_data=d))

    buttons_layout = []
    btn_i = 0
    row_i = 0
    while btn_i < len(buttons):
        row_layout = []
        for i in range(n_btn_in_row[row_i]):
            row_layout.append(buttons[btn_i])
            btn_i = btn_i + 1
        buttons_layout.append(row_layout)
        row_i = (row_i + 1) % len(n_btn_in_row)

    return InlineKeyboardMarkup(buttons_layout)


