from aiogram import types


def get_interface_for_admin():
    buttons = [
        [
            types.InlineKeyboardButton(
                text="Пользователи", callback_data="users"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Сотрудники", callback_data="workers"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Расписание", callback_data="schedule"
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


def get_interface_manage_schedule():
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
                text="Назад",
                callback_data="back admin",
            )
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_interface_manage_users():
    buttons = [
        [
            types.InlineKeyboardButton(
                text="Добавить пользователя", callback_data="add user"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Удалить пользователя", callback_data="delete user"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Посмотреть список клиентов",
                callback_data="show clients",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Посмотреть информацию о пользователе",
                callback_data="show user info",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Назад",
                callback_data="back admin",
            )
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_interface_manage_workers():
    buttons = [
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
                text="Назад",
                callback_data="back admin",
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


def generate_page_buttons(page: int, end: bool):
    buttons = []
    if page > 1:
        buttons.append(
            [
                types.InlineKeyboardButton(
                    text="Назад", callback_data=f"page:{page - 1}"
                )
            ]
        )
    if not end:
        buttons.append(
            [
                types.InlineKeyboardButton(
                    text="Вперед", callback_data=f"page:{page + 1}"
                )
            ]
        )
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_status():
    buttons = [
        [
            types.InlineKeyboardButton(
                text="Клиент", callback_data="chosen_status:client"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Администратор", callback_data="chosen_status:admin"
            )
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
