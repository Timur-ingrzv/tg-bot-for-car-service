from aiogram import types


def get_start_keyboard():
    buttons = [
        [
            types.InlineKeyboardButton(
                text="Посмотреть доступные услуги",
                callback_data="list services",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Войти в профиль", callback_data="authorization"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Зарегистрироваться", callback_data="registration"
            )
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
