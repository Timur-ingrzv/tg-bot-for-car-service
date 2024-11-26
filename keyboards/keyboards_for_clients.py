from aiogram import types


def get_interface_for_client():
    buttons = [
        [
            types.InlineKeyboardButton(
                text="Записаться в автосервис",
                callback_data="sign up for service",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Посмотреть записи",
                callback_data="show scheduler for client",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Выйти из профиля", callback_data="exit profile"
            )
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
