from aiogram import types


def get_interface_for_admin():
    buttons = [
        [
            types.InlineKeyboardButton(
                text="Добавить запись", callback_data="add record"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Удалить запись", callback_data="delete record"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Посмотреть записи в автосервис",
                callback_data="show records for admin",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Посмотреть информацию о работниках",
                callback_data="show workers info",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Изменить рабочее время сотрудника",
                callback_data="change working time",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Посмотреть рабочее время сотрудника",
                callback_data="show working time for worker",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Статистика", callback_data="statistic"
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
                text="Выйти из профиля", callback_data="exit profile"
            )
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_day_week():
    buttons = [
        [
            types.InlineKeyboardButton(
                text="Понедельник", callback_data="day_0"
            )
        ],
        [types.InlineKeyboardButton(text="Вторник", callback_data="day_1")],
        [types.InlineKeyboardButton(text="Среда", callback_data="day_2")],
        [types.InlineKeyboardButton(text="Четверг", callback_data="day_3")],
        [types.InlineKeyboardButton(text="Пятница", callback_data="day_4")],
        [types.InlineKeyboardButton(text="Суббота", callback_data="day_5")],
        [
            types.InlineKeyboardButton(
                text="Воскресенье", callback_data="day_6"
            )
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
