from aiogram import types


def get_interface_for_admin():
    buttons = [
        [
            types.InlineKeyboardButton(
                text="Добавить запись",
                callback_data="add record"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Удалить запись",
                callback_data="delete record"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Изменить данные профиля",
                callback_data="change profile data"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Выйти из профиля", callback_data="exit profile"
            )
        ]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
