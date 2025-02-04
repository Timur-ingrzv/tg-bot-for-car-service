from aiogram import types

from database.methods import db


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
                callback_data="change profile data",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Посмотреть свои записи",
                callback_data="show events for client",
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


async def get_services_to_add_schedule():
    services = await db.show_services()
    available_services = [(service["service_name"], service["price"]) for service in services]
    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"{service[0]} - {service[1]} руб.", callback_data=f"choose-service_{service[0]}"
            )
        ]
        for service in available_services
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
