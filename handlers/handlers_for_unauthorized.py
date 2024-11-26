from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.formatting import Bold, as_marked_section

from config import AVAILABLE_SERVICES
from keyboards import keyboards_for_unauthorized
from keyboards.keyboards_for_clients import get_interface_for_client
from utils.states import Registration, UserStatus
from database.methods import db

router = Router()


@router.callback_query(F.data == "services")
async def print_services(callback: types.CallbackQuery):
    new_list = "\n".join(
        [
            f"{i + 1}. {AVAILABLE_SERVICES[i]}"
            for i in range(len(AVAILABLE_SERVICES))
        ]
    )
    content = as_marked_section(Bold("Доступные услуги:"), new_list, marker="")
    await callback.message.answer(**content.as_kwargs())


@router.callback_query(StateFilter(None), F.data == "authorization")
async def enter_login(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите логин")
    await state.set_state(Registration.waiting_for_login)


@router.message(StateFilter(Registration.waiting_for_login))
async def enter_password(message: types.Message, state: FSMContext):
    await state.update_data(login=message.text)
    await message.answer("Введите пароль")
    await state.set_state(Registration.waiting_for_password)


@router.message(StateFilter(Registration.waiting_for_password))
async def authorization(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user = await db.find_user(user_data["login"], message.text)
    await state.clear()
    if not user:
        await message.answer(
            "Неверный логин или пароль\n"
            "Попробуйте еще раз или зарегистрируйтесь",
            reply_markup=keyboards_for_unauthorized.get_start_keyboard(),
        )
        return

    if "Ошибка" in user["status"]:
        await message.answer(user["status"])
    else:
        await state.update_data(user_id=user["id"])
        # выбираем интерфейс от статуса
        if user["status"] == "client":
            await state.set_state(UserStatus.client)
            interface = get_interface_for_client()
        else:
            await state.set_state(UserStatus.admin)
            interface = None

        await message.answer(
            f"С возвращением, {user['name']}", reply_markup=interface
        )


@router.callback_query(F.data == "registration")
async def registration(callback: types.CallbackQuery):
    pass
