from aiogram.fsm.state import StatesGroup, State


class Registration(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()


class UserStatus(StatesGroup):
    client = State()
    admin = State()
