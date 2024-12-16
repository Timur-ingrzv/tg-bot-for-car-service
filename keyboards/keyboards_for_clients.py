from aiogram import types

from config import AVAILABLE_SERVICES


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
                text="Посмотреть свободное время для записи",
                callback_data="show scheduler for client",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Изменить данные профиля",
                callback_data="change client profile data",
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


def get_interface_change_profile():
    buttons = [
        [
            types.InlineKeyboardButton(
                text="Имя", callback_data="change-client-profile_name"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Логин", callback_data="change-client-profile_login"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Пароль", callback_data="change-client-profile_password"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Номер телефона",
                callback_data="change-client-profile_phone_number",
            )
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_services_to_add_schedule():
    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"{service}", callback_data=f"choose-service_{service}"
            )
        ]
        for service in AVAILABLE_SERVICES
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
