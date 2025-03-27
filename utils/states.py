from aiogram.fsm.state import StatesGroup, State


class Authorization(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()


class UserStatus(StatesGroup):
    client = State()
    admin = State()
    unauthorized = State()


class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_phone_number = State()


class ChangeUserProfile(StatesGroup):
    waiting_for_new_value = State()


class SchedulerClient(StatesGroup):
    waiting_for_date_to_show_schedule = State()
    waiting_for_date_to_add_schedule = State()
    waiting_for_time_to_add_schedule = State()
    waiting_for_service_name_to_add_schedule = State()
    waiting_for_date_to_delete_schedule = State()
    waiting_for_time_to_delete_schedule = State()


class SchedulerAdmin(StatesGroup):
    waiting_for_client_name_to_add = State()
    waiting_for_worker_name_to_add = State()
    waiting_for_service_to_add = State()
    waiting_for_date_to_add = State()
    waiting_for_time_to_add = State()
    waiting_for_name_to_delete = State()
    waiting_for_date_to_delete = State()
    waiting_for_time_to_delete = State()
    waiting_for_start_to_show = State()
    waiting_for_end_to_show = State()


class WorkingTime(StatesGroup):
    waiting_worker_name = State()
    waiting_weekday = State()
    waiting_time = State()

    waiting_worker_name_to_show = State()

    waiting_worker_name_to_add = State()


class Statistic(StatesGroup):
    waiting_start_date = State()
    waiting_start_time = State()
    waiting_end_date = State()
    waiting_end_time = State()


class UsersAdmin(StatesGroup):
    waiting_for_name = State()
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_phone_number = State()
    waiting_for_status = State()

    waiting_for_name_to_delete = State()
    waiting_for_name_to_show_info = State()


class Services(StatesGroup):
    waiting_for_service_name_to_add = State()
    waiting_for_price_to_add = State()
    waiting_for_payout_to_add = State()

    waiting_for_service_name_to_delete = State()

    waiting_for_service_name_to_change = State()
    waiting_for_service_col_to_change = State()
    waiting_for_new_value_to_change = State()
