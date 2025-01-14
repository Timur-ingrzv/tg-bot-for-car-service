from datetime import datetime, timedelta, time

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext

from aiogram_calendar import (
    SimpleCalendar,
    get_user_locale,
    SimpleCalendarCallback,
)

from database.methods import db
from keyboards.keyboards_for_clients import get_services_to_add_schedule
from utils.states import SchedulerAdmin, UserStatus, SchedulerClient

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
