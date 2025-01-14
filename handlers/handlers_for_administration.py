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
from utils.states import SchedulerAdmin, UserStatus

router = Router()


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
