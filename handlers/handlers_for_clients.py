from datetime import datetime

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.methods import db
from keyboards.keyboards_for_clients import (
    get_interface_change_profile,
    get_services_to_add_schedule,
)
from utils.states import ChangeClientProfile, UserStatus, SchedulerClient
from config import AVAILABLE_SERVICES

router = Router()


@router.callback_query(F.data == "exit profile")
async def exit_profile(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    from bot import cmd_start, bot

    await cmd_start(callback.message, bot)


@router.callback_query(F.data == "change client profile data")
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
    await state.set_state(ChangeClientProfile.waiting_for_new_value)
    await callback.message.answer("Введите новое значение")


@router.message(StateFilter(ChangeClientProfile.waiting_for_new_value))
async def change_client_profile(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(UserStatus.client)
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
    await callback.message.answer("Введите желаемую дату в формате dd-mm-yyyy")


@router.message(StateFilter(SchedulerClient.waiting_for_date_to_show_schedule))
async def add_schedule(message: types.Message, state: FSMContext):
    await state.set_state(UserStatus.client)
    date = message.text
    try:
        valid_date = datetime.strptime(date.strip(), "%d-%m-%Y")
    except Exception as e:
        await message.answer("Неправильный формат даты")
        return

    res = await db.find_free_slots(valid_date)
    if not res:
        res = ["В данную дату нет свободных свободного времени"]
    await message.answer("\n".join(res))


@router.callback_query(F.data == "sign up for service")
async def input_date_to_add_schedule(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.set_state(SchedulerClient.waiting_for_date_to_add_schedule)
    await callback.message.answer(
        "Введите дату и время для записи в формате dd-mm-yyyy hours:minutes"
    )


@router.message(StateFilter(SchedulerClient.waiting_for_date_to_add_schedule))
async def input_service_name(message: types.Message, state: FSMContext):
    try:
        valid_date = datetime.strptime(message.text.strip(), "%d-%m-%Y %H:%M")
        await state.update_data(date=valid_date)
    except Exception as e:
        await state.set_state(UserStatus.client)
        await message.answer("Неправильный формат даты")
        return

    await state.set_state(
        SchedulerClient.waiting_for_service_name_to_add_schedule
    )
    await message.answer(
        "Выберите услугу", reply_markup=get_services_to_add_schedule()
    )


@router.callback_query(F.data.startswith("choose-service_"))
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
