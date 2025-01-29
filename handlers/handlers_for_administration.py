from datetime import datetime, timedelta, time

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext

from aiogram_calendar import (
    SimpleCalendar,
    get_user_locale,
    SimpleCalendarCallback,
)
import logging

from database.methods import db
from keyboards.keyboards_for_administration import get_day_week
from keyboards.keyboards_for_clients import get_services_to_add_schedule
from utils.states import SchedulerAdmin, UserStatus, ChangeWorkingTime

router = Router()


@router.callback_query(F.data == "add record")
async def input_client_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SchedulerAdmin.waiting_for_client_name_to_add)
    await callback.message.answer("Введите имя клиента")


@router.message(StateFilter(SchedulerAdmin.waiting_for_client_name_to_add))
async def input_worker_name(message: types.Message, state: FSMContext):
    await state.set_state(SchedulerAdmin.waiting_for_worker_name_to_add)
    await state.update_data(client_name=message.text.strip())
    await message.answer("Введите имя работника")


@router.message(StateFilter(SchedulerAdmin.waiting_for_worker_name_to_add))
async def input_service_name(message: types.Message, state: FSMContext):
    await state.set_state(SchedulerAdmin.waiting_for_service_to_add)
    await state.update_data(worker_name=message.text.strip())
    await message.answer(
        "Выберите услугу:", reply_markup=await get_services_to_add_schedule()
    )


@router.callback_query(
    StateFilter(SchedulerAdmin.waiting_for_service_to_add),
    F.data.startswith("choose-service_"),
)
async def input_date_to_add(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SchedulerAdmin.waiting_for_date_to_add)
    service_name = callback.data.split("_", maxsplit=1)[1]
    await state.update_data(service_name=service_name)
    calendar = SimpleCalendar(
        locale=await get_user_locale(callback.from_user), show_alerts=True
    )
    cur_time = datetime.now()
    calendar.set_dates_range(
        cur_time - timedelta(days=30), cur_time + timedelta(days=120)
    )
    await callback.message.answer(
        "Выберите дату для удаления записи",
        reply_markup=await calendar.start_calendar(
            year=cur_time.year, month=cur_time.month
        ),
    )


@router.callback_query(
    StateFilter(SchedulerAdmin.waiting_for_date_to_add),
    SimpleCalendarCallback.filter(),
)
async def input_time_to_add(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    calendar = SimpleCalendar(locale=await get_user_locale(callback.from_user))
    cur_date = datetime.now()
    calendar.set_dates_range(
        cur_date - timedelta(days=30), cur_date + timedelta(days=120)
    )
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.set_state(SchedulerAdmin.waiting_for_time_to_add)
        await state.update_data(date=date)
        await callback.message.answer("Введите время записи для добавления")


@router.message(StateFilter(SchedulerAdmin.waiting_for_time_to_add))
async def add_scheduler(message: types.Message, state: FSMContext):
    await state.set_state(UserStatus.admin)
    try:
        valid_time = int(message.text.strip())
        if not (0 <= valid_time < 24):
            await message.answer("Время должно быть в диапазоне от 0 до 23")
            return

        data = await state.get_data()
        valid_date = datetime.combine(data["date"], time(hour=valid_time))
        info = {
            "date": valid_date,
            "client_name": data["client_name"],
            "worker_name": data["worker_name"],
            "service_name": data["service_name"],
        }
        res = await db.add_schedule_admin(info)
        await message.answer(res)

    except Exception as e:
        await message.answer(
            "Неправильный формат времени - введите число от 0 до 23"
        )


@router.callback_query(F.data == "delete record")
async def input_name_to_delete(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.set_state(SchedulerAdmin.waiting_for_name_to_delete)
    await callback.message.answer("Введите имя клиента или работника")


@router.message(StateFilter(SchedulerAdmin.waiting_for_name_to_delete))
async def input_date_to_delete(message: types.Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(SchedulerAdmin.waiting_for_date_to_delete)
    calendar = SimpleCalendar(
        locale=await get_user_locale(message.from_user), show_alerts=True
    )
    cur_time = datetime.now()
    calendar.set_dates_range(
        cur_time - timedelta(days=30), cur_time + timedelta(days=120)
    )
    await message.answer(
        "Выберите дату для удаления записи",
        reply_markup=await calendar.start_calendar(
            year=cur_time.year, month=cur_time.month
        ),
    )


@router.callback_query(
    StateFilter(SchedulerAdmin.waiting_for_date_to_delete),
    SimpleCalendarCallback.filter(),
)
async def input_time_to_delete(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    calendar = SimpleCalendar(locale=await get_user_locale(callback.from_user))
    cur_date = datetime.now()
    calendar.set_dates_range(
        cur_date - timedelta(days=30), cur_date + timedelta(days=120)
    )
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.set_state(SchedulerAdmin.waiting_for_time_to_delete)
        await state.update_data(date=date)
        await callback.message.answer("Введите время записи для удаления")


@router.message(StateFilter(SchedulerAdmin.waiting_for_time_to_delete))
async def delete_scheduler(message: types.Message, state: FSMContext):
    await state.set_state(UserStatus.admin)
    try:
        valid_time = int(message.text.strip())
        if not (0 <= valid_time < 24):
            await state.set_state(UserStatus.client)
            await message.answer("Время должно быть в диапазоне от 0 до 23")
            return

        data = await state.get_data()
        valid_date = datetime.combine(data["date"], time(hour=valid_time))
        name = data["name"]
        res = await db.delete_schedule(name, valid_date)
        await message.answer(res)

    except Exception as e:
        await message.answer(
            "Неправильный формат времени - введите число от 0 до 23"
        )


@router.callback_query(F.data == "show records for admin")
async def input_start_date_to_show(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.set_state(SchedulerAdmin.waiting_for_start_to_show)
    calendar = SimpleCalendar(
        locale=await get_user_locale(callback.from_user), show_alerts=True
    )
    cur_time = datetime.now()
    calendar.set_dates_range(
        cur_time - timedelta(days=30), cur_time + timedelta(days=120)
    )
    await callback.message.answer(
        "Выберите дату начала диапазона для просмотра",
        reply_markup=await calendar.start_calendar(
            year=cur_time.year, month=cur_time.month
        ),
    )


@router.callback_query(
    StateFilter(SchedulerAdmin.waiting_for_start_to_show),
    SimpleCalendarCallback.filter(),
)
async def input_end_date_to_show(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    calendar = SimpleCalendar(locale=await get_user_locale(callback.from_user))
    cur_date = datetime.now()
    calendar.set_dates_range(
        cur_date - timedelta(days=30), cur_date + timedelta(days=120)
    )
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.set_state(SchedulerAdmin.waiting_for_end_to_show)
        await state.update_data(start=date)

        calendar = SimpleCalendar(
            locale=await get_user_locale(callback.from_user), show_alerts=True
        )
        cur_time = datetime.now()
        calendar.set_dates_range(
            cur_time - timedelta(days=30), cur_time + timedelta(days=120)
        )
        await callback.message.answer(
            "Выберите дату конца диапазона для просмотра",
            reply_markup=await calendar.start_calendar(
                year=cur_time.year, month=cur_time.month
            ),
        )


@router.callback_query(
    StateFilter(SchedulerAdmin.waiting_for_end_to_show),
    SimpleCalendarCallback.filter(),
)
async def show_schedule_for_admin(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    calendar = SimpleCalendar(locale=await get_user_locale(callback.from_user))
    cur_date = datetime.now()
    calendar.set_dates_range(
        cur_date - timedelta(days=30), cur_date + timedelta(days=120)
    )
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.set_state(UserStatus.admin)
        user_data = await state.get_data()
        start = user_data["start"]
        end = date
        if start > end:
            await callback.message.answer(
                "Начало диапазона должно быть раньше конца"
            )
            return
        schedule = await db.show_schedule_admin(start, end)
        if not schedule:
            await callback.message.answer("В данный период нет записей")
            return

        for note in schedule:
            await callback.message.answer(
                f"<b>Название услуги:</b> {note['service_name']}\n"
                f"<b>Клиент:</b> {note['client_name']}\n"
                f"<b>Работник:</b> {note['worker_name']}\n"
                f"<b>Цена:</b> {note['price']}\n"
                f"<b>Дата:</b> {note['date'].strftime('%d-%m-%Y %H-%M')}\n",
                parse_mode="HTML",
            )


@router.callback_query(F.data == "change working time")
async def input_worker_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChangeWorkingTime.waiting_worker_name)
    await callback.message.answer("Введите имя работника")


@router.message(StateFilter(ChangeWorkingTime.waiting_worker_name))
async def input_weekday(message: types.Message, state: FSMContext):
    worker_name = message.text.strip()
    worker = await db.find_worker(worker_name)
    if not worker:
        await state.set_state(UserStatus.admin)
        await message.answer("Работника с таким именем не существует")
        return

    await state.set_state(ChangeWorkingTime.waiting_weekday)
    await state.update_data(worker_id=worker["id"])
    await message.answer("Выберите день недели", reply_markup=get_day_week())


@router.callback_query(
    StateFilter(ChangeWorkingTime.waiting_weekday), F.data.startswith("day_")
)
async def input_time(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ChangeWorkingTime.waiting_time)
    weekday = int(callback.data.split("_")[1])
    await state.update_data(weekday=weekday)
    await callback.message.answer(
        "Введите время начала и конца рабочего времени"
        " в формате hours-hours(Если в этот день сотрудник"
        " не работает, то введите 0)"
    )


@router.message(StateFilter(ChangeWorkingTime.waiting_time))
async def change_working_time(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(UserStatus.admin)
    working_time = message.text.strip()
    if working_time == "0":
        res = await db.delete_working_time(
            int(data["worker_id"]), int(data["weekday"])
        )
        await message.answer(res)
        return

    try:
        start, end = map(int, working_time.split("-"))
        start = time(hour=start)
        end = time(hour=end)
        res = await db.add_working_time(
            int(data["worker_id"]), start, end, int(data["weekday"])
        )
        await message.answer(res)

    except Exception as e:
        logging.error(e)
        await message.answer("Неправильный формат времени")
