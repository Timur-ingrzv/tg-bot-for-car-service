from aiogram.fsm.state import StatesGroup, State


class Authorization(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()


class UserStatus(StatesGroup):
    client = State()
    admin = State()


class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_phone_number = State()


class ChangeClientProfile(StatesGroup):
    waiting_for_new_value = State()


class SchedulerClient(StatesGroup):
    waiting_for_date_to_show_schedule = State()
    waiting_for_date_to_add_schedule = State()
    waiting_for_service_name_to_add_schedule = State()
