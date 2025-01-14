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


from database.methods import db
from keyboards.keyboards_for_clients import (
    get_interface_change_profile,
    get_services_to_add_schedule,
)
from utils.states import ChangeUserProfile, UserStatus, SchedulerClient

router = Router()


@router.callback_query(F.data == "exit profile")
async def exit_profile(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    from bot import cmd_start, bot

    await cmd_start(callback.message, bot, state)


@router.callback_query(F.data == "change profile data")
async def change_profile_data(callback: types.CallbackQuery):
    await callback.message.answer(
        "Выберете поле, которое хотите изменить",
        reply_markup=get_interface_change_profile(),
    )


@router.callback_query(F.data.startswith("change-client-profile_"))
async def input_new_value(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(
        changed_field=callback.data.split("_", maxsplit=1)[1]
    )
    await state.set_state(ChangeUserProfile.waiting_for_new_value)
    await callback.message.answer("Введите новое значение")


@router.message(StateFilter(ChangeUserProfile.waiting_for_new_value))
async def change_user_profile(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data["status"] == "client":
        await state.set_state(UserStatus.client)
    else:
        await state.set_state(UserStatus.admin)
    changed_field = data["changed_field"]
    new_value = message.text.strip()
    if new_value == "":
        await message.answer("Новое значение не может быть пустой строкой")
        return

    if changed_field == "phone_number" and len(new_value) != 11:
        await message.answer("Новый номер телефона должен содержать 11 цифр")
        return

    result = await db.change_profile(data["user_id"], changed_field, new_value)
    await message.answer(result)


@router.callback_query(F.data == "show scheduler for client")
async def input_date_for_scheduler(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.set_state(SchedulerClient.waiting_for_date_to_show_schedule)
    calendar = SimpleCalendar(
        locale=await get_user_locale(callback.from_user), show_alerts=True
    )
    cur_time = datetime.now()
    calendar.set_dates_range(
        cur_time - timedelta(days=30), cur_time + timedelta(days=120)
    )
    await callback.message.answer(
        "Выберите желаемую дату",
        reply_markup=await calendar.start_calendar(
            year=cur_time.year, month=cur_time.month
        ),
    )


@router.callback_query(
    StateFilter(SchedulerClient.waiting_for_date_to_show_schedule),
    SimpleCalendarCallback.filter(),
)
async def show_schedule(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    await state.set_state(UserStatus.client)
    calendar = SimpleCalendar(locale=await get_user_locale(callback.from_user))
    cur_date = datetime.now()
    calendar.set_dates_range(
        cur_date - timedelta(days=30), cur_date + timedelta(days=120)
    )
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.set_state(UserStatus.client)
        if date < cur_date:
            await callback.message.answer("Выберите дату позже текущей")
            return
        res = await db.find_free_slots(date)
        if not res:
            res = ["В данную дату нет свободного времени"]
        ans = "\n".join(res)
        ans = f"Свободные слоты на {date.strftime('%d-%m-%Y')}:\n" + ans
        await callback.message.answer(ans)
    else:
        await state.set_state(UserStatus.client)
        await callback.message.answer("Произошла ошибка, повторите еще раз")


@router.callback_query(F.data == "sign up for service")
async def input_date_to_add_schedule(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.set_state(SchedulerClient.waiting_for_date_to_add_schedule)
    calendar = SimpleCalendar(
        locale=await get_user_locale(callback.from_user), show_alerts=True
    )
    cur_time = datetime.now()
    calendar.set_dates_range(
        cur_time - timedelta(days=30), cur_time + timedelta(days=120)
    )
    await callback.message.answer(
        "Выберите желаемую дату",
        reply_markup=await calendar.start_calendar(
            year=cur_time.year, month=cur_time.month
        ),
    )


@router.callback_query(
    StateFilter(SchedulerClient.waiting_for_date_to_add_schedule),
    SimpleCalendarCallback.filter(),
)
async def input_time_to_add_schedule(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    await state.set_state(UserStatus.client)
    calendar = SimpleCalendar(locale=await get_user_locale(callback.from_user))
    cur_date = datetime.now()
    calendar.set_dates_range(
        cur_date - timedelta(days=30), cur_date + timedelta(days=120)
    )
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.set_state(SchedulerClient.waiting_for_time_to_add_schedule)
        await state.update_data(date=date)
        await callback.message.answer("Введите желаемое время - час дня")
    else:
        await state.set_state(UserStatus.client)
        await callback.message.answer("Произошла ошибка, повторите еще раз")


@router.message(StateFilter(SchedulerClient.waiting_for_time_to_add_schedule))
async def input_service_name(message: types.Message, state: FSMContext):
    try:
        valid_time = int(message.text.strip())
        if not (0 <= valid_time < 24):
            await state.set_state(UserStatus.client)
            await message.answer("Время должно быть в диапазоне от 0 до 24")
            return

        data = await state.get_data()
        valid_date = datetime.combine(data["date"], time(hour=valid_time))
        await state.update_data(date=valid_date)

    except Exception as e:
        await state.set_state(UserStatus.client)
        await message.answer("Неправильный формат времени")
        return

    await state.set_state(
        SchedulerClient.waiting_for_service_name_to_add_schedule
    )
    await message.answer(
        "Выберите услугу", reply_markup=await get_services_to_add_schedule()
    )


@router.callback_query(
    StateFilter(SchedulerClient.waiting_for_service_name_to_add_schedule),
    F.data.startswith("choose-service_"),
)
async def add_schedule(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStatus.client)
    data = await state.get_data()
    service_name = callback.data.split("_", maxsplit=1)[1]
    info = {
        "date": data["date"],
        "client_id": data["user_id"],
        "service_name": service_name,
    }
    res = await db.add_schedule(info)
    await callback.message.answer(res)


@router.callback_query(F.data == "show events for client")
async def show_events(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    user_id = user_data["user_id"]
    res = await db.show_schedule(user_id)
    if isinstance(res, str):
        await callback.message.answer(res)
        return

    for note in res:
        await callback.message.answer(
            f"<b>Название услуги:</b> {note['service_name']}\n"
            f"<b>Цена:</b> {note['price']}\n"
            f"<b>Работник:</b> {note['name']}\n"
            f"<b>Дата:</b> {note['date'].strftime('%d-%m-%Y %H-%M')}\n",
            parse_mode="HTML",
        )
